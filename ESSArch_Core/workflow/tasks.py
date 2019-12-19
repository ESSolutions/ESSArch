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

import datetime
import errno
import logging
import os
import pathlib
import shutil
import tarfile
import tempfile
import zipfile

from celery import states as celery_states
from celery.exceptions import Ignore
from celery.result import allow_join_result
from crontab import CronTab
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils import timezone

# noinspection PyUnresolvedReferences
from ESSArch_Core import tasks  # noqa
from ESSArch_Core.auth.models import Notification
from ESSArch_Core.configuration.models import Path
from ESSArch_Core.essxml.util import parse_mets
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
from ESSArch_Core.storage.exceptions import (
    TapeDriveLockedError,
    TapeMountedAndLockedByOtherError,
    TapeMountedError,
    TapeUnmountedError,
)
from ESSArch_Core.storage.models import (
    Robot,
    RobotQueue,
    StorageObject,
    TapeDrive,
)
from ESSArch_Core.util import (
    creation_date,
    delete_path,
    find_destination,
    open_file,
    timestamp_to_datetime,
)
from ESSArch_Core.WorkflowEngine.dbtask import DBTask
from ESSArch_Core.WorkflowEngine.models import ProcessTask

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

        sip_profile = aip.submission_agreement.profile_sip

        try:
            shutil.rmtree(dst)
        except FileNotFoundError:
            pass

        if aip.policy.receive_extract_sip:
            temp = Path.objects.cached('entity', 'temp', 'value')
            with tempfile.TemporaryDirectory(dir=temp) as tmpdir:
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

                dst = os.path.join(dst, '')
                try:
                    os.makedirs(dst)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise

                tmpsrc = tmpdir
                if len(os.listdir(tmpdir)) == 1 and os.listdir(tmpdir)[0] == root_member_name:
                    new_tmpsrc = os.path.join(tmpdir, root_member_name)
                    if os.path.isdir(new_tmpsrc):
                        tmpsrc = new_tmpsrc

                self.logger.debug('Moving content of {} to {}'.format(tmpsrc, dst))

                for f in os.listdir(tmpsrc):
                    shutil.move(os.path.join(tmpsrc, f), dst)

                self.logger.debug('Deleting {}'.format(tmpdir))

            aip.sip_path = os.path.relpath(dst, aip.object_path)
        else:
            self.logger.debug('Copying {} to {}'.format(container, dst))
            shutil.copy2(container, dst)
            aip.sip_path = os.path.relpath(os.path.join(dst, os.path.basename(container)), aip.object_path)

        sip_mets_dir, sip_mets_file = find_destination('mets_file', sip_profile.structure, aip.sip_path)
        if os.path.isfile(aip.sip_path):
            sip_mets_data = parse_mets(
                open_file(
                    os.path.join(aip.object_path, sip_mets_dir, sip_mets_file),
                    container=aip.sip_path,
                    container_prefix=aip.object_identifier_value,
                )
            )
        else:
            sip_mets_data = parse_mets(open_file(os.path.join(aip.object_path, sip_mets_dir, sip_mets_file)))

        # prefix all SIP data
        sip_mets_data = {f'SIP_{k.upper()}': v for k, v in sip_mets_data.items()}

        aip_profile_rel_data = aip.get_profile_rel('aip').data
        aip_profile_rel_data.data.update(sip_mets_data)
        aip_profile_rel_data.save()

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
