import errno
import logging
import os
import shutil
import tarfile
import time
import uuid
from collections import OrderedDict

import jsonfield
from celery import states as celery_states
from celery.result import allow_join_result
from django.contrib.auth import get_user_model
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from glob2 import iglob
from os import walk
from weasyprint import HTML

from ESSArch_Core.WorkflowEngine.models import ProcessTask
from ESSArch_Core.configuration.models import Path
from ESSArch_Core.fixity.checksum import calculate_checksum
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.profiles.models import ProfileIP
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.search.ingest import index_path
from ESSArch_Core.util import (
    convert_file,
    creation_date,
    find_destination,
    timestamp_to_datetime,
)

logger = logging.getLogger('essarch.maintenance')
User = get_user_model()

ARCHIVAL_OBJECT = 'archival_object'
METADATA = 'metadata'
TYPE_CHOICES = (
    (ARCHIVAL_OBJECT, 'Archival Object'),
    (METADATA, 'Metadata'),
)


class MaintenanceRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # cron syntax, blank for manual only appraisal
    frequency = models.CharField(max_length=255, blank=True, default='')

    # empty for all files in IP or all fields in tree node
    specification = jsonfield.JSONField(null=True, default=None)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    public = models.BooleanField(default=True)

    class Meta:
        abstract = True


class MaintenanceJob(models.Model):
    STATUS_CHOICES = zip(celery_states.ALL_STATES, celery_states.ALL_STATES)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey('maintenance.MaintenanceRule', on_delete=models.SET_NULL, null=True, related_name='jobs')
    status = models.CharField(choices=STATUS_CHOICES, max_length=50, default=celery_states.PENDING)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        abstract = True
        get_latest_by = 'start_date'

    def _get_report_directory(self):
        entity = '%s_reports' % self.MAINTENANCE_TYPE

        try:
            return Path.objects.get(entity=entity).value
        except Path.DoesNotExist:
            raise Path.DoesNotExist('Path %s is not configured' % entity)

    def _generate_report(self):
        template = 'maintenance/%s_report.html' % self.MAINTENANCE_TYPE
        dstdir = self._get_report_directory()
        dst = os.path.join(dstdir, '%s.pdf' % self.pk)

        render = render_to_string(template, {'job': self, 'rule': self.rule})
        HTML(string=render).write_pdf(dst)

    def _mark_as_complete(self):
        self.status = celery_states.SUCCESS
        self.end_date = timezone.now()
        self.save(update_fields=['status', 'end_date'])

        try:
            self._generate_report()
        except Exception:
            logger.exception('Failed to generate report')
            raise

    def _run(self):
        raise NotImplementedError

    def run(self):
        try:
            self.status = celery_states.STARTED
            self.save(update_fields=['status'])

            report_dir = self._get_report_directory()

            if not os.path.isdir(report_dir):
                raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), report_dir)

            if not os.access(report_dir, os.W_OK):
                raise OSError(errno.EACCES, os.strerror(errno.EACCES), report_dir)

            self._run()
        except Exception:
            self.status = celery_states.FAILURE
            self.end_date = timezone.now()
            self.save(update_fields=['status', 'end_date'])
            raise

        self._mark_as_complete()


class MaintenanceJobEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey('maintenance.AppraisalJob', on_delete=models.CASCADE, related_name='entries')
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)

    class Meta:
        abstract = True


class AppraisalRule(MaintenanceRule):
    type = models.CharField(max_length=100, choices=TYPE_CHOICES, default=ARCHIVAL_OBJECT)
    information_packages = models.ManyToManyField('ip.InformationPackage', related_name='appraisal_rules')


class AppraisalJob(MaintenanceJob):
    rule = models.ForeignKey('maintenance.AppraisalRule', on_delete=models.SET_NULL, null=True, related_name='jobs')

    MAINTENANCE_TYPE = 'appraisal'

    class Meta(MaintenanceJob.Meta):
        permissions = (
            ('run_appraisaljob', 'Can run appraisal job'),
        )

    def _run_metadata(self):
        pass

    def _run_archive_object(self):
        def get_information_packages(job):
            return self.rule.information_packages.filter(
                active=True,
                appraisal_date__lte=timezone.now(),
            ).exclude(
                appraisal_job_entries__job=self,
            )

        ips = get_information_packages(self)

        for ip in ips.order_by('-cached').iterator():  # run cached IPs first
            while not ip.cached:
                with allow_join_result():
                    t, created = ProcessTask.objects.get_or_create(
                        name='workflow.tasks.CacheAIP',
                        information_package=ip,
                        defaults={'responsible': ip.responsible, 'eager': False}
                    )

                    if not created:
                        t.run()

                time.sleep(10)
                ip.refresh_from_db()

            # inactivate old generations
            InformationPackage.objects.filter(aic=ip.aic, generation__lte=ip.generation).update(active=False)

            policy = ip.policy
            srcdir = os.path.join(policy.cache_storage.value, ip.object_identifier_value)

            if not self.rule.specification:
                # register all files
                for root, dirs, files in walk(srcdir):
                    rel = os.path.relpath(root, srcdir)

                    for f in files:
                        fpath = os.path.join(root, f)
                        job_entry = AppraisalJobEntry.objects.create(
                            job=self,
                            start_date=timezone.now(),
                            ip=ip,
                            document=os.path.join(rel, f)
                        )
                        job_entry.end_date = timezone.now()
                        job_entry.save()
            else:
                new_ip = ip.create_new_generation(ip.state, ip.responsible, None)

                dstdir = os.path.join(policy.cache_storage.value, new_ip.object_identifier_value)

                new_ip.object_path = dstdir
                new_ip.save()

                aip_profile = new_ip.get_profile_rel('aip').profile
                aip_profile_data = new_ip.get_profile_data('aip')

                mets_dir, mets_name = find_destination("mets_file", aip_profile.structure)
                mets_path = os.path.join(srcdir, mets_dir, mets_name)

                # copy files to new generation
                shutil.copytree(srcdir, dstdir)

                # delete files specified in rule
                for pattern in self.rule.specification:
                    for path in iglob(dstdir + '/' + pattern):
                        if os.path.isdir(path):
                            for root, dirs, files in walk(path):
                                rel = os.path.relpath(root, dstdir)

                                for f in files:
                                    fpath = os.path.join(root, f)
                                    job_entry = AppraisalJobEntry.objects.create(
                                        job=self,
                                        start_date=timezone.now(),
                                        ip=ip,
                                        document=os.path.join(rel, f)
                                    )
                                    os.remove(fpath)
                                    job_entry.end_date = timezone.now()
                                    job_entry.save()

                        elif os.path.isfile(path):
                            rel = os.path.relpath(path, dstdir)

                            job_entry = AppraisalJobEntry.objects.create(
                                job=self,
                                start_date=timezone.now(),
                                ip=ip,
                                document=rel,
                            )
                            os.remove(path)
                            job_entry.end_date = timezone.now()
                            job_entry.save()

                # preserve new generation
                sa = new_ip.submission_agreement

                try:
                    os.remove(mets_path)
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise

                filesToCreate = OrderedDict()

                try:
                    premis_profile = new_ip.get_profile_rel('preservation_metadata').profile
                    premis_profile_data = ip.get_profile_data('preservation_metadata')
                except ProfileIP.DoesNotExist:
                    pass
                else:
                    premis_dir, premis_name = find_destination("preservation_description_file", aip_profile.structure)
                    premis_path = os.path.join(dstdir, premis_dir, premis_name)

                    try:
                        os.remove(premis_path)
                    except OSError as e:
                        if e.errno != errno.ENOENT:
                            raise

                    filesToCreate[premis_path] = {
                        'spec': premis_profile.specification,
                        'data': fill_specification_data(premis_profile_data, ip=new_ip, sa=sa),
                    }

                filesToCreate[mets_path] = {
                    'spec': aip_profile.specification,
                    'data': fill_specification_data(aip_profile_data, ip=new_ip, sa=sa),
                }

                t = ProcessTask.objects.create(
                    name='ESSArch_Core.tasks.GenerateXML',
                    params={
                        'filesToCreate': filesToCreate,
                        'folderToParse': dstdir,
                    },
                    responsible=new_ip.responsible,
                    information_package=new_ip,
                )
                t.run().get()

                dsttar = dstdir + '.tar'
                dstxml = dstdir + '.xml'

                objid = new_ip.object_identifier_value

                with tarfile.open(dsttar, 'w') as tar:
                    for root, dirs, files in walk(dstdir):
                        rel = os.path.relpath(root, dstdir)
                        for d in dirs:
                            src = os.path.join(root, d)
                            arc = os.path.join(objid, rel, d)
                            arc = os.path.normpath(arc)
                            index_path(new_ip, src)
                            tar.add(src, arc, recursive=False)

                        for f in files:
                            src = os.path.join(root, f)
                            index_path(new_ip, src)
                            tar.add(src, os.path.normpath(os.path.join(objid, rel, f)))

                algorithm = policy.get_checksum_algorithm_display()
                checksum = calculate_checksum(dsttar, algorithm=algorithm)

                info = fill_specification_data(new_ip.get_profile_data('aip_description'), ip=new_ip, sa=sa)
                info["_IP_CREATEDATE"] = timestamp_to_datetime(creation_date(dsttar)).isoformat()

                aip_desc_profile = new_ip.get_profile('aip_description')
                filesToCreate = {
                    dstxml: {
                        'spec': aip_desc_profile.specification,
                        'data': info
                    }
                }

                ProcessTask.objects.create(
                    name="ESSArch_Core.tasks.GenerateXML",
                    params={
                        "filesToCreate": filesToCreate,
                        "folderToParse": dsttar,
                        "extra_paths_to_parse": [mets_path],
                        "algorithm": algorithm,
                    },
                    information_package=new_ip,
                    responsible=new_ip.responsible,
                ).run().get()

                InformationPackage.objects.filter(pk=new_ip.pk).update(
                    message_digest=checksum, message_digest_algorithm=policy.checksum_algorithm,
                )

                ProcessTask.objects.create(
                    name='ESSArch_Core.tasks.UpdateIPSizeAndCount',
                    information_package=new_ip,
                    responsible=new_ip.responsible,
                ).run().get()

                t = ProcessTask.objects.create(
                    name='workflow.tasks.StoreAIP',
                    information_package=new_ip,
                    responsible=new_ip.responsible,
                )

                t.run()

        self._mark_as_complete()

    def _run(self):
        if self.rule.type == ARCHIVAL_OBJECT:
            return self._run_archive_object()

        return self._run_metadata()


class AppraisalJobEntry(MaintenanceJobEntry):
    job = models.ForeignKey('maintenance.AppraisalJob', on_delete=models.CASCADE, related_name='entries')

    # when type of rule is ARCHIVAL_OBJECT
    ip = models.ForeignKey(
        'ip.InformationPackage',
        on_delete=models.SET_NULL,
        null=True,
        related_name='appraisal_job_entries'
    )
    document = models.CharField(max_length=255, blank=True)

    # when type of rule is METADATA
    component = models.CharField(max_length=255, blank=True)
    component_field = models.CharField(max_length=255, blank=True)


class ConversionRule(MaintenanceRule):
    information_packages = models.ManyToManyField('ip.InformationPackage', related_name='conversion_rules')


class ConversionJob(MaintenanceJob):
    rule = models.ForeignKey('maintenance.ConversionRule', on_delete=models.SET_NULL, null=True, related_name='jobs')

    MAINTENANCE_TYPE = 'conversion'

    def _run(self):
        def get_information_packages(job):
            return self.rule.information_packages.filter(
                active=True,
            ).exclude(
                conversion_job_entries__job=self,
            )

        ips = get_information_packages(self)

        for ip in ips.order_by('-cached').iterator():  # convert cached IPs first
            while not ip.cached:
                with allow_join_result():
                    t, created = ProcessTask.objects.get_or_create(
                        name='workflow.tasks.CacheAIP',
                        information_package=ip,
                        defaults={'responsible': ip.responsible, 'eager': False}
                    )

                    if not created:
                        t.run()

                time.sleep(10)
                ip.refresh_from_db()

            policy = ip.policy
            srcdir = os.path.join(policy.cache_storage.value, ip.object_identifier_value)

            new_ip = ip.create_new_generation(ip.state, ip.responsible, None)

            dstdir = os.path.join(policy.cache_storage.value, new_ip.object_identifier_value)

            new_ip.object_path = dstdir
            new_ip.save()

            aip_profile = new_ip.get_profile_rel('aip').profile
            aip_profile_data = new_ip.get_profile_data('aip')

            mets_dir, mets_name = find_destination("mets_file", aip_profile.structure)
            mets_path = os.path.join(srcdir, mets_dir, mets_name)

            # copy files to new generation
            shutil.copytree(srcdir, dstdir)

            # convert files specified in rule
            for pattern, spec in self.rule.specification.items():
                target = spec['target']
                tool = spec['tool']

                for path in iglob(dstdir + '/' + pattern):
                    if os.path.isdir(path):
                        for root, dirs, files in walk(path):
                            rel = os.path.relpath(root, dstdir)

                            for f in files:
                                fpath = os.path.join(root, f)
                                job_entry = ConversionJobEntry.objects.create(
                                    job=self,
                                    start_date=timezone.now(),
                                    ip=ip,
                                    old_document=os.path.join(rel, f)
                                )
                                convert_file(fpath, target)

                                os.remove(fpath)

                                job_entry.new_document = os.path.splitext(job_entry.old_document)[0] + '.' + target
                                job_entry.end_date = timezone.now()
                                job_entry.tool = tool
                                job_entry.save()

                    elif os.path.isfile(path):
                        rel = os.path.relpath(path, dstdir)

                        job_entry = ConversionJobEntry.objects.create(
                            job=self,
                            start_date=timezone.now(),
                            ip=ip,
                            old_document=rel,
                        )
                        convert_file(path, target)

                        os.remove(path)

                        job_entry.new_document = os.path.splitext(job_entry.old_document)[0] + '.' + target
                        job_entry.end_date = timezone.now()
                        job_entry.tool = tool
                        job_entry.save()

            # preserve new generation
            sa = new_ip.submission_agreement

            try:
                os.remove(mets_path)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise

            filesToCreate = OrderedDict()

            try:
                premis_profile = new_ip.get_profile_rel('preservation_metadata').profile
                premis_profile_data = ip.get_profile_data('preservation_metadata')
            except ProfileIP.DoesNotExist:
                pass
            else:
                premis_dir, premis_name = find_destination("preservation_description_file", aip_profile.structure)
                premis_path = os.path.join(dstdir, premis_dir, premis_name)

                try:
                    os.remove(premis_path)
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise

                filesToCreate[premis_path] = {
                    'spec': premis_profile.specification,
                    'data': fill_specification_data(premis_profile_data, ip=new_ip, sa=sa),
                }

            filesToCreate[mets_path] = {
                'spec': aip_profile.specification,
                'data': fill_specification_data(aip_profile_data, ip=new_ip, sa=sa),
            }

            t = ProcessTask.objects.create(
                name='ESSArch_Core.tasks.GenerateXML',
                params={
                    'filesToCreate': filesToCreate,
                    'folderToParse': dstdir,
                },
                responsible=new_ip.responsible,
                information_package=new_ip,
            )
            t.run().get()

            dsttar = dstdir + '.tar'
            dstxml = dstdir + '.xml'

            objid = new_ip.object_identifier_value

            with tarfile.open(dsttar, 'w') as tar:
                for root, dirs, files in walk(dstdir):
                    rel = os.path.relpath(root, dstdir)
                    for d in dirs:
                        src = os.path.join(root, d)
                        arc = os.path.join(objid, rel, d)
                        arc = os.path.normpath(arc)
                        index_path(new_ip, src)
                        tar.add(src, arc, recursive=False)

                    for f in files:
                        src = os.path.join(root, f)
                        index_path(new_ip, src)
                        tar.add(src, os.path.normpath(os.path.join(objid, rel, f)))

            algorithm = policy.get_checksum_algorithm_display()
            checksum = calculate_checksum(dsttar, algorithm=algorithm)

            info = fill_specification_data(new_ip.get_profile_data('aip_description'), ip=new_ip, sa=sa)
            info["_IP_CREATEDATE"] = timestamp_to_datetime(creation_date(dsttar)).isoformat()

            aip_desc_profile = new_ip.get_profile('aip_description')
            filesToCreate = {
                dstxml: {
                    'spec': aip_desc_profile.specification,
                    'data': info
                }
            }

            ProcessTask.objects.create(
                name="ESSArch_Core.tasks.GenerateXML",
                params={
                    "filesToCreate": filesToCreate,
                    "folderToParse": dsttar,
                    "extra_paths_to_parse": [mets_path],
                    "algorithm": algorithm,
                },
                information_package=new_ip,
                responsible=new_ip.responsible,
            ).run().get()

            InformationPackage.objects.filter(pk=new_ip.pk).update(
                message_digest=checksum, message_digest_algorithm=policy.checksum_algorithm,
            )

            ProcessTask.objects.create(
                name='ESSArch_Core.tasks.UpdateIPSizeAndCount',
                information_package=new_ip,
                responsible=new_ip.responsible,
            ).run().get()

            t = ProcessTask.objects.create(
                name='workflow.tasks.StoreAIP',
                information_package=new_ip,
                responsible=new_ip.responsible,
            )

            t.run()


class ConversionJobEntry(MaintenanceJobEntry):
    job = models.ForeignKey('maintenance.ConversionJob', on_delete=models.CASCADE, related_name='entries')

    ip = models.ForeignKey(
        'ip.InformationPackage',
        on_delete=models.SET_NULL,
        null=True,
        related_name='conversion_job_entries'
    )
    old_document = models.CharField(max_length=255, blank=True)
    new_document = models.CharField(max_length=255, blank=True)
    tool = models.CharField(max_length=255, blank=True)
