import errno
import logging
import os
import shutil
import uuid
from operator import itemgetter
from os import walk
from pathlib import PurePath
from typing import List, Optional, cast

from celery import states as celery_states
from celery.result import allow_join_result
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from glob2 import iglob
from weasyprint import HTML

from ESSArch_Core.auth.models import Notification
from ESSArch_Core.configuration.models import Path
from ESSArch_Core.fields import JSONField
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.storage.exceptions import NoReadableStorage
from ESSArch_Core.storage.models import StorageObject
from ESSArch_Core.util import convert_file, has_write_access, in_directory
from ESSArch_Core.WorkflowEngine.util import create_workflow

logger = logging.getLogger('essarch.maintenance')
User = get_user_model()

ARCHIVAL_OBJECT = 'archival_object'
METADATA = 'metadata'
TYPE_CHOICES = (
    (ARCHIVAL_OBJECT, 'Archival Object'),
    (METADATA, 'Metadata'),
)


def find_all_files(datadir, ip, pattern):
    found_files = []
    for path in iglob(datadir + '/' + pattern):
        if os.path.isdir(path):
            for root, _dirs, files in walk(path):
                rel = os.path.relpath(root, datadir)

                for f in files:
                    found_files.append({'ip': ip.object_identifier_value, 'document': os.path.join(rel, f)})

        else:
            rel = os.path.relpath(path, datadir)
            found_files.append({'ip': ip.object_identifier_value, 'document': rel})
    return found_files


class MaintenanceTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # empty for all files in IP
    package_file_pattern = JSONField(null=True, default=None)

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    public = models.BooleanField(default=True)

    class Meta:
        abstract = True


class MaintenanceJob(models.Model):
    STATUS_CHOICES = sorted(zip(celery_states.ALL_STATES, celery_states.ALL_STATES), key=itemgetter(0))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=255)
    template = models.ForeignKey(
        'maintenance.MaintenanceTemplate', on_delete=models.SET_NULL,
        null=True, related_name='jobs',
    )
    information_packages = models.ManyToManyField('ip.InformationPackage', related_name='maintenenace_jobs')
    status = models.CharField(choices=STATUS_CHOICES, max_length=50, default=celery_states.PENDING)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    task = models.ForeignKey(
        'WorkflowEngine.ProcessTask', null=True, on_delete=models.SET_NULL, related_name='maintenance_jobs',
    )

    class Meta:
        abstract = True
        get_latest_by = 'start_date'
        ordering = ('-start_date',)

    def _get_report_directory(self):
        entity = '%s_reports' % self.MAINTENANCE_TYPE

        try:
            return Path.objects.get(entity=entity).value
        except Path.DoesNotExist:
            raise Path.DoesNotExist('Path %s is not configured' % entity)

    def get_report_pdf_path(self):
        path = self._get_report_directory()
        return os.path.join(path, str(self.pk) + '.pdf')

    def _generate_report(self):
        logger.info(f"User '{self.user}' generating report with of type '{self.MAINTENANCE_TYPE}'")
        template = 'maintenance/%s_report.html' % self.MAINTENANCE_TYPE
        dst = self.get_report_pdf_path()

        render = render_to_string(template, {'job': self, 'rule': self.template})
        HTML(string=render).write_pdf(dst)

    def create_notification(self, status):
        if status == celery_states.SUCCESS:
            msg = f'Completed maintenance job "{self.label or str(self.pk)}"'
            level = logging.INFO
        else:
            msg = f'Maintenance job "{self.label or str(self.pk)}" failed'
            level = logging.ERROR

        return Notification.objects.create(
            message=msg,
            level=level,
            user=self.user,
            refresh=True,
        )

    def _mark_as_complete(self):
        try:
            self._generate_report()
        except Exception:
            msg = 'Failed to generate report'
            Notification.objects.create(
                message=msg,
                level=logging.WARN,
                user=self.user,
                refresh=False,
            )
            logger.exception(msg)
        finally:
            self.status = celery_states.SUCCESS
            self.end_date = timezone.now()
            self.save(update_fields=['status', 'end_date'])

            if self.user is not None:
                self.create_notification(self.status)

    def _run(self):
        raise NotImplementedError

    def run(self):
        try:
            self.start_date = timezone.now()
            self.status = celery_states.STARTED
            self.save(update_fields=['status', 'start_date'])

            report_dir = self._get_report_directory()

            if not os.path.isdir(report_dir):
                raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), report_dir)

            if not has_write_access(report_dir):
                raise OSError(errno.EACCES, os.strerror(errno.EACCES), report_dir)

            self._run()
        except Exception:
            self.status = celery_states.FAILURE
            self.end_date = timezone.now()
            self.save(update_fields=['status', 'end_date'])
            self.create_notification(self.status)
            raise

        self._mark_as_complete()


class MaintenanceJobEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey('maintenance.AppraisalJob', on_delete=models.CASCADE, related_name='entries')
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)

    class Meta:
        abstract = True


class AppraisalTemplate(MaintenanceTemplate):
    type = models.CharField(max_length=100, choices=TYPE_CHOICES, default=ARCHIVAL_OBJECT)


class AppraisalJob(MaintenanceJob):
    template = models.ForeignKey(
        'maintenance.AppraisalTemplate', on_delete=models.SET_NULL,
        null=True, related_name='jobs',
    )
    information_packages = models.ManyToManyField('ip.InformationPackage', related_name='appraisal_jobs')
    task = models.ForeignKey(
        'WorkflowEngine.ProcessTask', null=True, on_delete=models.SET_NULL, related_name='appraisal_jobs',
    )
    package_file_pattern = JSONField(null=True, default=None)

    MAINTENANCE_TYPE = 'appraisal'

    class Meta(MaintenanceJob.Meta):
        permissions = (
            ('run_appraisaljob', 'Can run appraisal job'),
        )

    def preview(self):
        ips = self.information_packages.filter(
            Q(
                Q(appraisal_date__lte=timezone.now()) |
                Q(appraisal_date__isnull=True)
            ),
            active=True,
        )
        found_files = []
        for ip in ips:
            storage_obj = ip.storage.fastest().first()
            if storage_obj is None:
                raise StorageObject.DoesNotExist(
                    'No storage object available for {}'.format(ip.object_identifier_value),
                )
            if self.package_file_pattern:
                for pattern in self.package_file_pattern:
                    found_files.extend(
                        [{'ip': ip.object_identifier_value, 'document': f} for f in storage_obj.list_files(pattern)]
                    )
            else:
                found_files.extend(
                    [{'ip': ip.object_identifier_value, 'document': f} for f in storage_obj.list_files()]
                )

        return found_files

    def create_notification(self, status):
        if status == celery_states.SUCCESS:
            msg = f'Completed appraisal job "{self.label or str(self.pk)}"'
            level = logging.INFO
        else:
            msg = f'Appraisal job "{self.label or str(self.pk)}" failed'
            level = logging.ERROR

        return Notification.objects.create(
            message=msg,
            level=level,
            user=self.user,
            refresh=True,
        )

    @transaction.atomic
    def _run(self):
        def get_information_packages():
            return self.information_packages.filter(
                Q(
                    Q(appraisal_date__lte=timezone.now()) |
                    Q(appraisal_date__isnull=True)
                ),
                active=True,
            ).exclude(
                appraisal_job_entries__job=self,
            )

        def delete_file(old_ip, filepath, relpath):
            entry = AppraisalJobEntry.objects.create(
                job=self,
                start_date=timezone.now(),
                ip=old_ip,
                document=relpath
            )
            os.remove(filepath)
            entry.end_date = timezone.now()
            entry.save()
            return entry

        entries = []
        for t in self.tags.all():
            entries.append(
                AppraisalJobEntry(
                    job=self,
                    start_date=timezone.now(),
                    end_date=timezone.now(),
                    component=t.versions.latest().name,
                )
            )
        AppraisalJobEntry.objects.bulk_create(entries)
        self.tags.all().delete()

        ips = get_information_packages()
        logger.info('Running appraisal job {} on {} information packages'.format(self.pk, ips.count()))

        delete_packages = getattr(settings, 'DELETE_PACKAGES_ON_APPRAISAL', False)
        tmpdir = Path.objects.cached('entity', 'temp', 'value')

        for ip in ips.iterator():
            storage_obj: Optional[StorageObject] = ip.storage.readable().fastest().first()
            if storage_obj is None:
                raise NoReadableStorage

            ip_tmpdir = os.path.join(tmpdir, ip.object_identifier_value)
            os.makedirs(ip_tmpdir, exist_ok=True)
            storage_obj.read(ip_tmpdir, None, extract=True)

            if not self.package_file_pattern:
                # register all files
                job_entry_start_date = timezone.now()
                job_entry_end_date = timezone.now()
                job_entries = []
                for root, _dirs, files in walk(ip_tmpdir):
                    for f in files:
                        rel = PurePath(os.path.join(root, f)).relative_to(ip_tmpdir).as_posix()
                        job_entries.append(
                            AppraisalJobEntry(
                                job=self,
                                start_date=job_entry_start_date,
                                end_date=job_entry_end_date,
                                ip=ip,
                                document=rel,
                            )
                        )

                AppraisalJobEntry.objects.bulk_create(job_entries)

                if delete_packages:
                    for storage_obj in ip.storage.all():
                        storage_obj.delete_files()
                    ip.delete()
                else:
                    # inactivate old generations
                    InformationPackage.objects.filter(aic=ip.aic, generation__lte=ip.generation).update(active=False)

            else:
                new_ip = ip.create_new_generation(ip.state, ip.responsible, None)
                new_ip_tmpdir = os.path.join(tmpdir, new_ip.object_identifier_value)
                storage_obj.read(new_ip_tmpdir, None, extract=True)
                new_ip.object_path = new_ip_tmpdir
                new_ip.save()

                # delete files specified in rule
                for pattern in cast(List[str], self.package_file_pattern):
                    for path in iglob(new_ip_tmpdir + '/' + pattern):
                        if not in_directory(path, new_ip_tmpdir):
                            raise ValueError('Invalid file-pattern accessing files outside of package')

                        if os.path.isdir(path):
                            for root, _dirs, files in walk(path):
                                for f in files:
                                    rel = PurePath(os.path.join(root, f)).relative_to(new_ip_tmpdir).as_posix()
                                    delete_file(ip, os.path.join(root, f), rel)

                            shutil.rmtree(path)

                        else:
                            rel = PurePath(path).relative_to(new_ip_tmpdir).as_posix()
                            delete_file(ip, path, rel)

                if delete_packages:
                    for storage_obj in ip.storage.all():
                        storage_obj.delete_files()
                    ip.delete()
                else:
                    # inactivate old generations
                    InformationPackage.objects.filter(aic=ip.aic, generation__lte=ip.generation).update(active=False)

                with allow_join_result():
                    preserve_new_generation(new_ip)


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


class ConversionTemplate(MaintenanceTemplate):
    pass


def preserve_new_generation(new_ip):
    workflow = new_ip.create_preservation_workflow()
    workflow = create_workflow(workflow, new_ip, name='Preserve Information Package', eager=True)
    workflow.run()


class ConversionJob(MaintenanceJob):
    template = models.ForeignKey(
        'maintenance.ConversionTemplate', on_delete=models.SET_NULL,
        null=True, related_name='jobs',
    )
    information_packages = models.ManyToManyField('ip.InformationPackage', related_name='conversion_jobs')
    task = models.ForeignKey(
        'WorkflowEngine.ProcessTask', null=True, on_delete=models.SET_NULL, related_name='conversion_jobs',
    )
    specification = JSONField(null=True, default=None)

    MAINTENANCE_TYPE = 'conversion'

    def preview(self):
        ips = self.information_packages.all()
        found_files = []
        for ip in ips:
            storage_target = ip.policy.cache_storage.enabled_target.target
            datadir = os.path.join(storage_target, ip.object_identifier_value)
            for pattern, _spec in self.specification.items():
                found_files.extend(find_all_files(datadir, ip, pattern))
        return found_files

    def create_notification(self, status):
        if status == celery_states.SUCCESS:
            msg = f'Completed conversion job "{self.label or str(self.pk)}"'
            level = logging.INFO
        else:
            msg = f'Conversion job "{self.label or str(self.pk)}" failed'
            level = logging.ERROR

        return Notification.objects.create(
            message=msg,
            level=level,
            user=self.user,
            refresh=True,
        )

    def _run(self):
        def get_information_packages():
            return self.information_packages.filter(
                active=True,
            ).exclude(
                conversion_job_entries__job=self,
            )

        ips = get_information_packages()

        for ip in ips.order_by('-cached').iterator():  # convert cached IPs first
            policy = ip.policy

            srcdir = os.path.join(policy.cache_storage.enabled_target.target, ip.object_identifier_value)
            new_ip = ip.create_new_generation(ip.state, ip.responsible, None)

            tmpdir = Path.objects.cached('entity', 'temp', 'value')
            dstdir = os.path.join(tmpdir, new_ip.object_identifier_value)

            new_ip.object_path = dstdir
            new_ip.save()

            # copy files to new generation
            shutil.copytree(srcdir, dstdir)

            # convert files specified in rule
            for pattern, spec in self.specification.items():
                target = spec['target']
                tool = spec['tool']

                for path in iglob(dstdir + '/' + pattern):
                    if os.path.isdir(path):
                        for root, _dirs, files in walk(path):
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
            preserve_new_generation(new_ip)


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
