"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import copy
import datetime
import errno
import logging
import os
import pathlib
import shutil
import tarfile
import uuid
import zipfile
from os import walk

from celery import states as celery_states
from celery.exceptions import Ignore
from celery.result import allow_join_result
from crontab import CronTab
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from groups_manager.utils import get_permission_name
from guardian.shortcuts import assign_perm

# noinspection PyUnresolvedReferences
from ESSArch_Core import tasks  # noqa
from ESSArch_Core.auth.models import Member, Notification
from ESSArch_Core.configuration.models import Path, StoragePolicy
from ESSArch_Core.essxml.Generator.xmlGenerator import (
    XMLGenerator,
    parseContent,
)
from ESSArch_Core.fixity.checksum import calculate_checksum
from ESSArch_Core.ip.models import (
    MESSAGE_DIGEST_ALGORITHM_CHOICES_DICT,
    InformationPackage,
    Workarea,
)
from ESSArch_Core.maintenance.models import (
    AppraisalJob,
    AppraisalRule,
    ConversionJob,
    ConversionRule,
)
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.search.importers import get_backend as get_importer
from ESSArch_Core.search.ingest import index_path
from ESSArch_Core.storage.exceptions import (
    TapeDriveLockedError,
    TapeMountedAndLockedByOtherError,
    TapeMountedError,
    TapeUnmountedError,
)
from ESSArch_Core.storage.models import (
    TAPE,
    IOQueue,
    Robot,
    RobotQueue,
    StorageMethod,
    StorageObject,
    TapeDrive,
)
from ESSArch_Core.tags.models import Tag, TagStructure, TagVersion
from ESSArch_Core.util import (
    creation_date,
    delete_path,
    find_destination,
    get_tree_size_and_count,
    timestamp_to_datetime,
)
from ESSArch_Core.WorkflowEngine.dbtask import DBTask
from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask

User = get_user_model()
logger = logging.getLogger('essarch')


class ReceiveSIP(DBTask):
    logger = logging.getLogger('essarch.workflow.tasks.ReceiveSIP')
    event_type = 20100

    @transaction.atomic
    def run(self, purpose=None, delete_sip=False):
        self.logger.debug('Receiving SIP')
        aip = InformationPackage.objects.get(pk=self.ip)
        algorithm = aip.get_checksum_algorithm()
        container = aip.object_path
        objid, container_type = os.path.splitext(os.path.basename(container))
        container_type = container_type.lower()
        xml = aip.package_mets_path
        aip.package_mets_create_date = timestamp_to_datetime(creation_date(xml)).isoformat()
        aip.package_mets_size = os.path.getsize(xml)
        aip.package_mets_digest_algorithm = MESSAGE_DIGEST_ALGORITHM_CHOICES_DICT[algorithm.upper()]
        aip.package_mets_digest = calculate_checksum(xml, algorithm=algorithm)
        aip.generation = 0
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC, responsible=aip.responsible,
                                                label=aip.label, start_date=aip.start_date, end_date=aip.end_date)
        old_sip_path = aip.object_path
        aip.aic = aic
        aip_dir = os.path.join(aip.policy.ingest_path.value, objid)
        aip.object_path = aip_dir
        try:
            os.makedirs(aip_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        aip.save()

        dst_path, dst_name = find_destination('sip', aip.get_profile('aip').structure, aip.object_path)
        if dst_path is None:
            dst_path, dst_name = find_destination('content', aip.get_profile('aip').structure, aip.object_path)

        dst_name, = self.parse_params(dst_name)
        dst = os.path.join(dst_path, dst_name)

        if aip.policy.receive_extract_sip:
            tmpdir = Path.objects.cached('entity', 'temp', 'value')
            self.logger.debug('Extracting {} to {}'.format(container, tmpdir))
            if container_type == '.tar':
                with tarfile.open(container) as tar:
                    root_member_name = tar.getnames()[0]
                    tar.extractall(tmpdir)
            elif container_type == '.zip':
                with zipfile.ZipFile(container) as zipf:
                    root_member_name = zipf.namelist()[0]
                    zipf.extractall(tmpdir)
            else:
                raise ValueError('Invalid container type: {}'.format(container))

            tmp_root = os.path.join(tmpdir, root_member_name)
            dst = os.path.join(dst, '')
            try:
                os.makedirs(dst)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
            self.logger.debug('Moving content of {} to {}'.format(tmp_root, dst))
            for f in os.listdir(tmp_root):
                shutil.move(os.path.join(tmp_root, f), dst)
            self.logger.debug('Deleting {}'.format(tmp_root))
            aip.sip_path = os.path.relpath(dst, aip.object_path)
        else:
            self.logger.debug('Copying {} to {}'.format(container, dst))
            shutil.copy2(container, dst)
            aip.sip_path = os.path.relpath(os.path.join(dst, os.path.basename(container)), aip.object_path)

        if delete_sip:
            delete_path(old_sip_path)
            delete_path(pathlib.Path(old_sip_path).with_suffix('.xml'))

        self.logger.debug('sip_path set to {}'.format(aip.sip_path))
        aip.save()

    def event_outcome_success(self, result, purpose=None, delete_sip=False):
        return "Received SIP"


class ReceiveAIP(DBTask):
    event_type = 30710

    def run(self, workarea):
        workarea = Workarea.objects.prefetch_related('ip').get(pk=workarea)
        ip = workarea.ip

        ip.state = 'Receiving'
        ip.save(update_fields=['state'])

        ingest = ip.policy.ingest_path
        dst = os.path.join(ingest.value, ip.object_identifier_value)

        shutil.copytree(ip.object_path, dst)

        ip.object_path = dst
        ip.state = 'Received'
        ip.save()


class CacheAIP(DBTask):
    event_type = 30310

    def run(self):
        aip_obj = InformationPackage.objects.prefetch_related('policy').get(pk=self.ip)
        policy = aip_obj.policy
        srcdir = aip_obj.object_path
        objid = aip_obj.object_identifier_value

        dstdir = os.path.join(policy.cache_storage.value, objid)
        dsttar = dstdir + '.tar'
        dstxml = dstdir + '.xml'

        try:
            os.makedirs(dstdir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        tag_structure = None
        indexed_files = []

        data = fill_specification_data(aip_obj.get_profile_data('aip'), ip=aip_obj, sa=aip_obj.submission_agreement)
        ctsdir, ctsfile = find_destination('content_type_specification', aip_obj.get_profile('aip').structure, srcdir)
        ct_profile = aip_obj.get_profile('content_type')

        if ct_profile is not None:
            cts = parseContent(os.path.join(ctsdir, ctsfile), data)
            if os.path.isfile(cts):
                logger.info('Found content type specification: {path}'.format(path=cts))
                try:
                    ct_importer_name = ct_profile.specification['name']
                except KeyError:
                    logger.exception('No content type importer specified in profile')
                    raise
                ct_importer = get_importer(ct_importer_name)(self.get_processtask())
                indexed_files = ct_importer.import_content(cts, ip=aip_obj)
            else:
                err = "Content type specification not found"
                logger.error('{err}: {path}'.format(err=err, path=cts))
                raise OSError(errno.ENOENT, err, cts)

        elif aip_obj.tag is not None:
            with transaction.atomic():
                tag = Tag.objects.create()
                tag_structure = TagStructure.objects.create(tag=tag, parent=aip_obj.tag,
                                                            structure=aip_obj.tag.structure)
                TagVersion.objects.create(tag=tag, name=objid, type='Information Package',
                                          elastic_index='component')

        with tarfile.open(dsttar, 'w') as tar:
            for root, dirs, files in walk(srcdir):
                rel = os.path.relpath(root, srcdir)
                for d in dirs:
                    src = os.path.join(root, d)
                    arc = os.path.join(objid, rel, d)
                    arc = os.path.normpath(arc)

                    index_path(aip_obj, src)

                    tar.add(src, arc, recursive=False)

                    try:
                        os.makedirs(os.path.normpath(os.path.join(dstdir, rel, d)))
                    except OSError as e:
                        if e.errno != errno.EEXIST:
                            raise

                for f in files:
                    src = os.path.join(root, f)
                    dst = os.path.join(dstdir, rel, f)
                    dst = os.path.normpath(dst)

                    try:
                        # check if file has already been indexed
                        indexed_files.remove(src)
                    except ValueError:
                        # file has not been indexed, index it
                        index_path(aip_obj, src, parent=tag_structure)

                    shutil.copy2(src, dst)
                    tar.add(src, os.path.normpath(os.path.join(objid, rel, f)))

        algorithm = policy.get_checksum_algorithm_display().upper()
        checksum = calculate_checksum(dsttar, algorithm=algorithm)

        info = fill_specification_data(
            aip_obj.get_profile_data('aip_description'),
            ip=aip_obj, sa=aip_obj.submission_agreement
        )
        info["_IP_CREATEDATE"] = timestamp_to_datetime(creation_date(dsttar)).isoformat()

        aip_desc_profile = aip_obj.get_profile('aip_description')
        filesToCreate = {
            dstxml: {
                'spec': aip_desc_profile.specification,
                'data': info
            }
        }

        aip_profile = aip_obj.get_profile_rel('aip').profile
        mets_dir, mets_name = find_destination("mets_file", aip_profile.structure)
        mets_path = os.path.join(srcdir, mets_dir, mets_name)
        generator = XMLGenerator()
        generator.generate(filesToCreate, folderToParse=dsttar, extra_paths_to_parse=[mets_path], algorithm=algorithm)

        size, count = get_tree_size_and_count(aip_obj.object_path)
        InformationPackage.objects.filter(pk=self.ip).update(
            message_digest=checksum, message_digest_algorithm=policy.checksum_algorithm,
            object_size=size, object_num_items=count,
        )

        aicxml = os.path.join(policy.cache_storage.value, str(aip_obj.aic.pk) + '.xml')
        aicinfo = fill_specification_data(aip_obj.get_profile_data('aic_description'), ip=aip_obj.aic)
        aic_desc_profile = aip_obj.get_profile('aic_description')

        filesToCreate = {
            aicxml: {
                'spec': aic_desc_profile.specification,
                'data': aicinfo
            }
        }

        parsed_files = []

        for ip in aip_obj.aic.information_packages.order_by('generation'):
            parsed_files.append({
                'FName': ip.object_identifier_value + '.tar',
                'FExtension': 'tar',
                'FDir': '',
                'FParentDir': '',
                'FChecksum': ip.message_digest,
                'FID': str(uuid.uuid4()),
                'daotype': "borndigital",
                'href': ip.object_identifier_value + '.tar',
                'FMimetype': 'application/x-tar',
                'FCreated': ip.create_date,
                'FFormatName': 'Tape Archive Format',
                'FFormatVersion': 'None',
                'FFormatRegistryKey': 'x-fmt/265',
                'FSize': str(ip.object_size),
                'FUse': 'Datafile',
                'FChecksumType': ip.get_message_digest_algorithm_display(),
                'FLoctype': 'URL',
                'FLinkType': 'simple',
                'FChecksumLib': 'ESSArch',
                'FIDType': 'UUID',
            })

        generator = XMLGenerator()
        generator.generate(filesToCreate, parsed_files=parsed_files, algorithm=algorithm)

        InformationPackage.objects.filter(pk=self.ip).update(
            object_path=dstdir, cached=True
        )
        shutil.rmtree(srcdir)
        if policy.ingest_delete:
            reception = Path.objects.values_list('value', flat=True).get(entity='ingest_reception')
            reception_tar = os.path.join(reception, objid + '.tar')
            reception_xml = os.path.join(reception, objid + '.xml')
            reception_events_xml = os.path.join(reception, objid + '_ipevents.xml')
            for f in [reception_tar, reception_xml, reception_events_xml]:
                try:
                    os.remove(f)
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise
        return self.ip

    def event_outcome_success(self, result, *args, **kwargs):
        return "Cached AIP '%s'" % self.get_information_package().object_identifier_value


class StoreAIP(DBTask):
    hidden = True

    def run(self):
        objid, aic, size = InformationPackage.objects.values_list(
            'object_identifier_value', 'aic_id', 'object_size'
        ).get(pk=self.ip)
        policy = InformationPackage.objects.prefetch_related('policy__storage_methods__targets').get(pk=self.ip).policy

        if not policy:
            raise StoragePolicy.DoesNotExist("No policy found in IP: '%s'" % objid)

        storage_methods = policy.storage_methods.secure_storage().filter(status=True)

        if not storage_methods.exists():
            raise StorageMethod.DoesNotExist("No available longterm storage methods found in policy: '%s'" % policy)

        aic = str(aic)
        cache_dir = policy.cache_storage.value
        xml_file = os.path.join(cache_dir, objid) + '.xml'
        xml_size = os.path.getsize(xml_file)
        aic_xml_file = os.path.join(cache_dir, aic) + '.xml'
        aic_xml_size = os.path.getsize(aic_xml_file)

        step = ProcessStep.objects.create(
            name='Write to storage',
            parent_step_id=self.step,
            information_package_id=self.ip,
        )

        with transaction.atomic():
            for method in storage_methods:
                for method_target in method.storage_method_target_relations.filter(status=1):
                    req_type = 10 if method_target.storage_method.type == TAPE else 15

                    entry, created = IOQueue.objects.get_or_create(
                        storage_method_target=method_target, req_type=req_type,
                        ip_id=self.ip, status__in=[0, 2, 5],
                        defaults={
                            'user_id': self.responsible, 'status': 0,
                            'write_size': size + xml_size + aic_xml_size
                        }
                    )

                    if created:
                        InformationPackage.objects.filter(pk=self.ip).update(state='Preserving')

                    entry.step = step
                    entry.save(update_fields=['step'])

    def event_outcome_success(self, result, *args, **kwargs):
        return "Created entries in IO queue for AIP '%s'" % self.get_information_package().object_identifier_value


class AccessAIP(DBTask):
    def run(self, aip, storage_object=None, tar=True, extracted=False, new=False, package_xml=False,
            aic_xml=False, object_identifier_value="", dst=None):
        aip = InformationPackage.objects.get(pk=aip)
        responsible = User.objects.get(pk=self.responsible)

        # if it is a received IP, i.e. from ingest and not from storage,
        # then we read it directly from disk and move it to the ingest workarea
        if aip.state == 'Received':
            if not extracted and not new:
                raise ValueError('An IP must be extracted when transferred to ingest workarea')

            if new:
                # Create new generation of the IP

                old_aip = aip.pk
                new_aip = aip.create_new_generation('Ingest Workarea', responsible, object_identifier_value)
                aip = InformationPackage.objects.get(pk=old_aip)
            else:
                new_aip = aip

            workarea = Path.objects.get(entity='ingest_workarea').value
            workarea_user = os.path.join(workarea, responsible.username)
            dst_dir = os.path.join(workarea_user, new_aip.object_identifier_value, )

            shutil.copytree(aip.object_path, dst_dir)

            workarea_obj = Workarea.objects.create(
                ip=new_aip, user_id=self.responsible, type=Workarea.INGEST, read_only=not new
            )
            Notification.objects.create(
                message="%s is now in workarea" % new_aip.object_identifier_value,
                level=logging.INFO, user_id=self.responsible, refresh=True
            )

            if new:
                new_aip.object_path = dst_dir
                new_aip.save(update_fields=['object_path'])

            return str(workarea_obj.pk)

        if storage_object is not None:
            storage_object = StorageObject.objects.get(pk=storage_object)
        else:
            storage_object = aip.get_fastest_readable_storage_object()

        aip.access(storage_object, self.get_processtask(), dst=dst)


class PrepareDIP(DBTask):
    logger = logging.getLogger('essarch.tasks.PrepareDIP')

    def run(self, label, object_identifier_value=None, orders=[]):
        disseminations = Path.objects.get(entity='disseminations').value

        perms = copy.deepcopy(getattr(settings, 'IP_CREATION_PERMS_MAP', {}))

        ip = InformationPackage.objects.create(
            object_identifier_value=object_identifier_value,
            label=label,
            responsible_id=self.responsible,
            state="Prepared",
            package_type=InformationPackage.DIP,
        )

        self.ip = ip.pk
        ip.orders.add(*orders)

        member = Member.objects.get(django_user__id=self.responsible)
        user_perms = perms.pop('owner', [])
        organization = member.django_user.user_profile.current_organization
        organization.assign_object(ip, custom_permissions=perms)
        organization.add_object(ip)

        for perm in user_perms:
            perm_name = get_permission_name(perm, ip)
            assign_perm(perm_name, member.django_user, ip)

        ProcessTask.objects.filter(pk=self.request.id).update(
            information_package=ip,
        )

        ProcessStep.objects.filter(tasks__pk=self.request.id).update(
            information_package=ip,
        )

        ip_dir = os.path.join(disseminations, ip.object_identifier_value)
        os.mkdir(ip_dir)

        ip.object_path = ip_dir
        ip.save(update_fields=['object_path'])

        return ip.pk

    def event_outcome_success(self, result, label, object_identifier_value=None, orders=[]):
        return 'Prepared DIP "%s"' % self.ip


class CreateDIP(DBTask):
    event_type = 30600

    def run(self, ip):
        ip = InformationPackage.objects.get(pk=ip)

        if ip.package_type != InformationPackage.DIP:
            raise ValueError('"%s" is not a DIP, it is a "%s"' % (ip, ip.package_type))

        ip.state = 'Creating'
        ip.save(update_fields=['state'])

        src = ip.object_path
        order_path = Path.objects.get(entity='orders').value

        order_count = ip.orders.count()

        for idx, order in enumerate(ip.orders.all()):
            dst = os.path.join(order_path, str(order.pk), ip.object_identifier_value)
            shutil.copytree(src, dst)

            self.set_progress(idx + 1, order_count)

        ip.state = 'Created'
        ip.save(update_fields=['state'])

    def event_outcome_success(self, result, ip):
        return 'Created DIP "%s"' % ip


class PollRobotQueue(DBTask):
    track = False

    def run(self):
        force_entries = RobotQueue.objects.filter(
            req_type=30, status__in=[0, 2]
        ).select_related('storage_medium').order_by('-status', 'posted')

        non_force_entries = RobotQueue.objects.filter(
            status__in=[0, 2]
        ).exclude(req_type=30).select_related('storage_medium').order_by('-status', '-req_type', 'posted')[:5]

        entries = list(force_entries) + list(non_force_entries)

        if not len(entries):
            raise Ignore()

        for entry in entries:
            entry.status = 2
            entry.save(update_fields=['status'])

            medium = entry.storage_medium

            if entry.req_type == 10:  # mount
                if medium.tape_drive is not None:  # already mounted
                    if hasattr(entry, 'io_queue_entry'):  # mounting for read or write
                        if medium.tape_drive.io_queue_entry != entry.io_queue_entry:
                            raise TapeMountedAndLockedByOtherError(
                                "Tape already mounted and locked by '%s'" % medium.tape_drive.io_queue_entry
                            )

                        entry.delete()

                    raise TapeMountedError("Tape already mounted")

                drive = entry.tape_drive

                if drive is None:
                    free_drive = TapeDrive.objects.filter(
                        status=20, storage_medium__isnull=True, io_queue_entry__isnull=True, locked=False,
                    ).order_by('num_of_mounts').first()

                    if free_drive is None:
                        raise ValueError('No tape drive available')

                    drive = free_drive

                free_robot = Robot.objects.filter(robot_queue__isnull=True).first()

                if free_robot is None:
                    raise ValueError('No robot available')

                entry.robot = free_robot
                entry.status = 5
                entry.save(update_fields=['robot', 'status'])

                with allow_join_result():

                    try:
                        ProcessTask.objects.create(
                            name="ESSArch_Core.tasks.MountTape",
                            params={
                                'medium': medium.pk,
                                'drive': drive.pk,
                            }
                        ).run().get()
                    except TapeMountedError:
                        entry.delete()
                        raise
                    except BaseException:
                        entry.status = 100
                        raise
                    else:
                        medium.tape_drive = drive
                        medium.save(update_fields=['tape_drive'])
                        entry.delete()
                    finally:
                        entry.robot = None
                        entry.save(update_fields=['robot', 'status'])

            elif entry.req_type in [20, 30]:  # unmount
                if medium.tape_drive is None:  # already unmounted
                    entry.delete()
                    raise TapeUnmountedError("Tape already unmounted")

                if medium.tape_drive.locked:
                    if entry.req_type == 20:
                        raise TapeDriveLockedError("Tape locked")

                free_robot = Robot.objects.filter(robot_queue__isnull=True).first()

                if free_robot is None:
                    raise ValueError('No robot available')

                entry.robot = free_robot
                entry.status = 5
                entry.save(update_fields=['robot', 'status'])

                with allow_join_result():
                    try:
                        ProcessTask.objects.create(
                            name="ESSArch_Core.tasks.UnmountTape",
                            params={
                                'drive': medium.tape_drive.pk,
                            }
                        ).run().get()
                    except TapeUnmountedError:
                        entry.delete()
                        raise
                    except BaseException:
                        entry.status = 100
                        raise
                    else:
                        medium.tape_drive = None
                        medium.save(update_fields=['tape_drive'])
                        entry.delete()
                    finally:
                        entry.robot = None
                        entry.save(update_fields=['robot', 'status'])


class UnmountIdleDrives(DBTask):
    track = False

    def run(self):
        idle_drives = TapeDrive.objects.filter(
            status=20, storage_medium__isnull=False,
            last_change__lte=timezone.now() - F('idle_time'),
            locked=False,
        )

        if not idle_drives.exists():
            raise Ignore()

        for drive in idle_drives.iterator():
            robot_queue_entry_exists = RobotQueue.objects.filter(
                storage_medium=drive.storage_medium, req_type=20, status__in=[0, 2]
            ).exists()
            if not robot_queue_entry_exists:
                RobotQueue.objects.create(
                    user=User.objects.get(username='system'),
                    storage_medium=drive.storage_medium,
                    req_type=20, status=0,
                )


class ScheduleAppraisalJobs(DBTask):
    track = False

    def run(self):
        now = timezone.now()

        # get rules without future jobs scheduled
        rules = AppraisalRule.objects.filter(
            information_packages__isnull=False, information_packages__active=True,
            information_packages__appraisal_date__lte=now
        ).exclude(jobs__start_date__gte=now).exclude(frequency__exact='')

        for rule in rules.iterator():
            cron_entry = CronTab(rule.frequency)

            try:
                latest_job = rule.jobs.latest()
                delay = cron_entry.next(timezone.localtime(latest_job.start_date))
                last = latest_job.start_date
            except AppraisalJob.DoesNotExist:
                # no job has been created yet
                delay = cron_entry.next(timezone.localtime(now))
                last = now

            next_date = last + datetime.timedelta(seconds=delay)
            AppraisalJob.objects.create(rule=rule, start_date=next_date)


class PollAppraisalJobs(DBTask):
    track = False

    def run(self):
        now = timezone.now()
        jobs = AppraisalJob.objects.select_related('rule').filter(status=celery_states.PENDING, start_date__lte=now)

        for job in jobs.iterator():
            job.run()


class ScheduleConversionJobs(DBTask):
    track = False

    def run(self):
        now = timezone.now()

        # get rules without future jobs scheduled
        rules = ConversionRule.objects.filter(
            information_packages__isnull=False, information_packages__active=True,
        ).exclude(jobs__start_date__gte=now).exclude(frequency__exact='')

        for rule in rules.iterator():
            cron_entry = CronTab(rule.frequency)

            try:
                latest_job = rule.jobs.latest()
                delay = cron_entry.next(timezone.localtime(latest_job.start_date))
                last = latest_job.start_date
            except ConversionJob.DoesNotExist:
                # no job has been created yet
                delay = cron_entry.next(timezone.localtime(now))
                last = now

            next_date = last + datetime.timedelta(seconds=delay)
            ConversionJob.objects.create(rule=rule, start_date=next_date)


class PollConversionJobs(DBTask):
    track = False

    def run(self):
        now = timezone.now()
        jobs = ConversionJob.objects.select_related('rule').filter(status=celery_states.PENDING, start_date__lte=now)

        for job in jobs.iterator():
            job.run()
