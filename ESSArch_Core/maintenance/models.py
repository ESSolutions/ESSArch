import errno
import logging
import os
import shutil
import uuid
from operator import itemgetter
from os import walk

from celery import states as celery_states
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from glob2 import iglob
from weasyprint import HTML

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.fields import JSONField
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.util import convert_file, find_destination, has_write_access
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

        elif os.path.isfile(path):
            rel = os.path.relpath(path, datadir)
            found_files.append({'ip': ip.object_identifier_value, 'document': rel})
    return found_files


class MaintenanceRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # cron syntax, blank for manual only appraisal
    frequency = models.CharField(max_length=255, blank=True, default='')

    # empty for all files in IP or all fields in tree node
    specification = JSONField(null=True, default=None)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    public = models.BooleanField(default=True)

    class Meta:
        abstract = True


class MaintenanceJob(models.Model):
    STATUS_CHOICES = sorted(zip(celery_states.ALL_STATES, celery_states.ALL_STATES), key=itemgetter(0))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey('maintenance.MaintenanceRule', on_delete=models.SET_NULL, null=True, related_name='jobs')
    status = models.CharField(choices=STATUS_CHOICES, max_length=50, default=celery_states.PENDING)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

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

    def _generate_report(self):
        logger.info(f"User '{self.user}' generating report with of type '{self.MAINTENANCE_TYPE}'")
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

            if not has_write_access(report_dir):
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

    def get_job_preview_files(self):
        ips = self.information_packages.filter(
            Q(
                Q(appraisal_date__lte=timezone.now()) |
                Q(appraisal_date__isnull=True)
            ),
            active=True,
        )
        found_files = []
        for ip in ips:
            storage_target = ip.policy.cache_storage.enabled_target.target
            datadir = os.path.join(storage_target, ip.object_identifier_value)
            if self.specification:
                for pattern in self.specification:
                    found_files.extend(find_all_files(datadir, ip, pattern))
            else:
                for root, _dirs, files in walk(datadir):
                    rel = os.path.relpath(root, datadir)

                    for f in files:
                        found_files.append({'ip': ip.object_identifier_value, 'document': os.path.join(rel, f)})
        return found_files


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
        def get_information_packages():
            return self.rule.information_packages.filter(
                Q(
                    Q(appraisal_date__lte=timezone.now()) |
                    Q(appraisal_date__isnull=True)
                ),
                active=True,
            ).exclude(
                appraisal_job_entries__job=self,
            )

        ips = get_information_packages()
        logger.info('Running appraisal job {} on {} information packages'.format(self.pk, ips.count()))

        for ip in ips.iterator():
            # inactivate old generations
            InformationPackage.objects.filter(aic=ip.aic, generation__lte=ip.generation).update(active=False)

            policy = ip.policy
            srcdir = os.path.join(policy.cache_storage.enabled_target.target, ip.object_identifier_value)

            if not self.rule.specification:
                # register all files
                for root, _dirs, files in walk(srcdir):
                    rel = os.path.relpath(root, srcdir)

                    for f in files:
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

                tmpdir = Path.objects.cached('entity', 'temp', 'value')
                dstdir = os.path.join(tmpdir, new_ip.object_identifier_value)

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
                            for root, _dirs, files in walk(path):
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
                preserve_new_generation(aip_profile, aip_profile_data, dstdir, ip, mets_path, new_ip, policy)

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

    def get_job_preview_files(self):
        ips = self.information_packages.all()
        found_files = []
        for ip in ips:
            storage_target = ip.policy.cache_storage.enabled_target.target
            datadir = os.path.join(storage_target, ip.object_identifier_value)
            for pattern, _spec in self.specification.items():
                found_files.extend(find_all_files(datadir, ip, pattern))
        return found_files


def preserve_new_generation(aip_profile, aip_profile_data, dstdir, ip, mets_path, new_ip, policy):
    workflow = new_ip.create_preservation_workflow()
    workflow = create_workflow(workflow, new_ip, name='Preserve Information Package', eager=True)
    workflow.run()


class ConversionJob(MaintenanceJob):
    rule = models.ForeignKey('maintenance.ConversionRule', on_delete=models.SET_NULL, null=True, related_name='jobs')

    MAINTENANCE_TYPE = 'conversion'

    def _run(self):
        def get_information_packages():
            return self.rule.information_packages.filter(
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
            preserve_new_generation(aip_profile, aip_profile_data, dstdir, ip, mets_path, new_ip, policy)


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
