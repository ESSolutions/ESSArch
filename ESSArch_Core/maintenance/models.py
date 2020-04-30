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
from django.template.loader import render_to_string
from django.utils import timezone
from glob2 import iglob
from weasyprint import HTML

from ESSArch_Core.auth.models import Notification
from ESSArch_Core.configuration.models import EventType, Path
from ESSArch_Core.essxml.Generator.xmlGenerator import parseContent
from ESSArch_Core.fields import JSONField
from ESSArch_Core.fixity.models import ConversionTool
from ESSArch_Core.ip.models import EventIP, InformationPackage
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.storage.exceptions import NoReadableStorage
from ESSArch_Core.storage.models import StorageObject
from ESSArch_Core.util import (
    find_destination,
    has_write_access,
    in_directory,
    normalize_path,
)
from ESSArch_Core.WorkflowEngine.util import create_workflow

logger = logging.getLogger('essarch.maintenance')
User = get_user_model()

ARCHIVAL_OBJECT = 'archival_object'
METADATA = 'metadata'
TYPE_CHOICES = (
    (ARCHIVAL_OBJECT, 'Archival Object'),
    (METADATA, 'Metadata'),
)


class MaintenanceTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    public = models.BooleanField(default=True)

    class Meta:
        abstract = True


class MaintenanceJob(models.Model):
    STATUS_CHOICES = sorted(zip(celery_states.ALL_STATES, celery_states.ALL_STATES), key=itemgetter(0))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=255)
    purpose = models.TextField(blank=False)
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

    def get_report_context(self):
        return {'job': self, 'rule': self.template}

    def _generate_report(self):
        logger.info(f"User '{self.user}' generating report with of type '{self.MAINTENANCE_TYPE}'")
        template = 'maintenance/%s_report.html' % self.MAINTENANCE_TYPE
        dst = self.get_report_pdf_path()

        render = render_to_string(template, self.get_report_context())
        HTML(string=render).write_pdf(dst)

    def create_notification(self, status):
        raise NotImplementedError

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

    # empty for all files in IP
    package_file_pattern = JSONField(null=True, default=None)


class AppraisalJob(MaintenanceJob):
    template = models.ForeignKey(
        'maintenance.AppraisalTemplate', on_delete=models.SET_NULL,
        null=True, related_name='jobs',
    )
    information_packages = models.ManyToManyField('ip.InformationPackage', related_name='appraisal_jobs')
    tags = models.ManyToManyField('tags.Tag', related_name='appraisal_jobs')
    task = models.ForeignKey(
        'WorkflowEngine.ProcessTask', null=True, on_delete=models.SET_NULL, related_name='appraisal_jobs',
    )
    package_file_pattern = JSONField(null=True, default=None)

    MAINTENANCE_TYPE = 'appraisal'

    class Meta(MaintenanceJob.Meta):
        permissions = (
            ('run_appraisaljob', 'Can run appraisal job'),
        )

    def preview(self, ip: InformationPackage):
        storage_obj = ip.storage.readable().fastest().first()
        if storage_obj is None:
            raise NoReadableStorage

        if self.package_file_pattern:
            for pattern in self.package_file_pattern:
                yield from storage_obj.list_files(pattern, case_sensitive=False)
        else:
            yield from storage_obj.list_files()

    def get_report_context(self):
        return {
            'job': self,
            'rule': self.template,
            'ip_entries': self.entries.filter(ip__isnull=False),
            'tag_entries': self.entries.filter(ip__isnull=True),
        }

    def create_notification(self, status):
        if self.user is None:
            return

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

    def delete_file(self, old_ip, filepath, relpath, new_ip):
        filepath, relpath = normalize_path(filepath), normalize_path(relpath)
        entry = AppraisalJobEntry.objects.create(
            job=self,
            start_date=timezone.now(),
            ip=old_ip,
            document=relpath
        )
        os.remove(filepath)
        entry.end_date = timezone.now()
        entry.save()

        EventIP.objects.create(
            eventType=self.delete_event_type,
            eventOutcome=EventIP.SUCCESS,
            eventOutcomeDetailNote='Deleted {}'.format(relpath),
            linkingObjectIdentifierValue=new_ip.object_identifier_value,
        )
        return entry

    def delete_document_tags(self, ip, new_ip, new_ip_tmpdir):
        ip_tag_documents = self.tags.select_related('current_version').filter(
            information_package=ip, current_version__elastic_index='document',
        )

        for t in ip_tag_documents:
            tag_relpath = os.path.join(
                t.current_version.custom_fields['href'],
                t.current_version.custom_fields['filename'],
            )
            tag_filepath = os.path.join(new_ip_tmpdir, tag_relpath)

            try:
                self.delete_file(ip, tag_filepath, tag_relpath, new_ip)
            except FileNotFoundError:
                pass

            t.delete()

    @transaction.atomic
    def _run(self):
        self.delete_event_type = EventType.objects.get(eventType=50710)
        entries = []

        for t in self.tags.select_related('current_version').exclude(current_version__elastic_index='document').all():
            entries.append(
                AppraisalJobEntry(
                    job=self,
                    start_date=timezone.now(),
                    end_date=timezone.now(),
                    component=t.current_version,
                )
            )

        AppraisalJobEntry.objects.bulk_create(entries)

        ips = self.information_packages
        logger.info('Running appraisal job {} on {} information packages'.format(self.pk, ips.count()))

        delete_packages = getattr(settings, 'DELETE_PACKAGES_ON_APPRAISAL', False)
        tmpdir = Path.objects.get(entity='temp').value

        for ip in ips.iterator():
            storage_obj: Optional[StorageObject] = ip.storage.readable().fastest().first()
            if storage_obj is None:
                raise NoReadableStorage

            if not self.package_file_pattern:
                ip_tmpdir = os.path.join(tmpdir, ip.object_identifier_value)
                os.makedirs(ip_tmpdir, exist_ok=True)
                storage_obj.read(ip_tmpdir, None, extract=True)

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
                        EventIP.objects.create(
                            eventType=self.delete_event_type,
                            eventOutcome=EventIP.SUCCESS,
                            eventOutcomeDetailNote='Deleted {}'.format(rel),
                            linkingObjectIdentifierValue=ip.object_identifier_value,
                        )

                AppraisalJobEntry.objects.bulk_create(job_entries)

                if delete_packages:
                    for storage_obj in ip.storage.all():
                        storage_obj.delete_files()
                    ip.delete()
                else:
                    # inactivate old generations
                    InformationPackage.objects.filter(
                        aic=ip.aic, generation__lte=ip.generation
                    ).update(active=False, last_changed_local=timezone.now())

            else:
                new_ip = ip.create_new_generation(ip.state, ip.responsible, None)
                new_ip_tmpdir = os.path.join(tmpdir, new_ip.object_identifier_value)
                storage_obj.read(new_ip_tmpdir, None, extract=True)
                new_ip.object_path = new_ip_tmpdir
                new_ip.save()

                # delete files specified in rule
                for pattern in cast(List[str], self.package_file_pattern):
                    for path in iglob(new_ip_tmpdir + '/' + pattern, case_sensitive=False):
                        if not in_directory(path, new_ip_tmpdir):
                            raise ValueError('Invalid file-pattern accessing files outside of package')

                        if os.path.isdir(path):
                            for root, _dirs, files in walk(path):
                                for f in files:
                                    rel = PurePath(os.path.join(root, f)).relative_to(new_ip_tmpdir).as_posix()
                                    self.delete_file(ip, os.path.join(root, f), rel, new_ip)

                            shutil.rmtree(path)

                        else:
                            rel = PurePath(path).relative_to(new_ip_tmpdir).as_posix()
                            self.delete_file(ip, path, rel, new_ip)

                self.delete_document_tags(ip, new_ip, new_ip_tmpdir)

                with allow_join_result():
                    preserve_new_generation(new_ip)

                ip.tags.exclude(
                    current_version__elastic_index='document',
                ).update(information_package=new_ip)

                if delete_packages:
                    for storage_obj in ip.storage.all():
                        storage_obj.delete_files()
                    ip.delete()
                else:
                    # inactivate old generations
                    InformationPackage.objects.filter(aic=ip.aic, generation__lte=ip.generation).update(active=False)
                    ip.tags.filter(current_version__elastic_index='document').delete()

        document_tag_ips = InformationPackage.objects.exclude(appraisal_jobs=self).filter(
            tags__appraisal_jobs=self,
            tags__current_version__elastic_index='document',
        ).distinct()
        for ip in document_tag_ips.iterator():
            storage_obj: Optional[StorageObject] = ip.storage.readable().fastest().first()
            if storage_obj is None:
                raise NoReadableStorage

            new_ip = ip.create_new_generation(ip.state, ip.responsible, None)
            new_ip_tmpdir = os.path.join(tmpdir, new_ip.object_identifier_value)
            storage_obj.read(new_ip_tmpdir, None, extract=True)
            new_ip.object_path = new_ip_tmpdir
            new_ip.save()

            self.delete_document_tags(ip, new_ip, new_ip_tmpdir)

            with allow_join_result():
                preserve_new_generation(new_ip)

            ip.tags.exclude(
                current_version__elastic_index='document',
            ).update(information_package=new_ip)

            if delete_packages:
                for storage_obj in ip.storage.all():
                    storage_obj.delete_files()
                ip.delete()
            else:
                # inactivate old generations
                InformationPackage.objects.filter(aic=ip.aic, generation__lte=ip.generation).update(active=False)
                ip.tags.filter(current_version__elastic_index='document').delete()

        self.tags.all().delete()


class AppraisalJobEntry(MaintenanceJobEntry):
    job = models.ForeignKey('maintenance.AppraisalJob', on_delete=models.CASCADE, related_name='entries')

    ip = models.ForeignKey(
        'ip.InformationPackage',
        on_delete=models.SET_NULL,
        null=True,
        related_name='appraisal_job_entries'
    )
    document = models.CharField(max_length=255, blank=True)

    component = models.CharField(max_length=255, blank=True)
    component_field = models.CharField(max_length=255, blank=True)


class ConversionTemplate(MaintenanceTemplate):
    specification = JSONField(null=True, default=None)


def preserve_new_generation(new_ip):
    generate_premis = new_ip.profile_locked('preservation_metadata')
    has_representations = find_destination(
        "representations", new_ip.get_structure(), new_ip.object_path,
    )[1] is not None

    # remove existing premis and mets paths:
    mets_path = os.path.join(new_ip.object_path, new_ip.get_content_mets_file_path())
    try:
        os.remove(mets_path)
    except FileNotFoundError:
        pass

    events_file = os.path.join(new_ip.object_path, new_ip.get_events_file_path())
    try:
        os.remove(events_file)
    except FileNotFoundError:
        pass

    if generate_premis:
        premis_profile_data = new_ip.get_profile_data('preservation_metadata')
        data = fill_specification_data(premis_profile_data, ip=new_ip)
        premis_path = parseContent(new_ip.get_premis_file_path(), data)
        try:
            os.remove(premis_path)
        except FileNotFoundError:
            pass

    workflow = [
        {
            "step": True,
            "name": "Generate AIP",
            "children": [
                {
                    "name": "ESSArch_Core.ip.tasks.DownloadSchemas",
                    "label": "Download Schemas",
                },
                {
                    "step": True,
                    "name": "Create Log File",
                    "children": [
                        {
                            "name": "ESSArch_Core.ip.tasks.GenerateEventsXML",
                            "label": "Generate events xml file",
                        },
                        {
                            "name": "ESSArch_Core.tasks.AppendEvents",
                            "label": "Add events to xml file",
                        },
                        {
                            "name": "ESSArch_Core.ip.tasks.AddPremisIPObjectElementToEventsFile",
                            "label": "Add premis IP object to xml file",
                        },

                    ]
                },
                {
                    "name": "ESSArch_Core.ip.tasks.GeneratePremis",
                    "if": generate_premis,
                    "label": "Generate premis",
                },
                {
                    "name": "ESSArch_Core.ip.tasks.GenerateContentMets",
                    "label": "Generate content-mets",
                },
            ]
        },
        {
            "step": True,
            "name": "Validate AIP",
            "children": [
                {
                    "name": "ESSArch_Core.tasks.ValidateXMLFile",
                    "label": "Validate content-mets",
                    "params": {
                        "xml_filename": "{{_CONTENT_METS_PATH}}",
                    }
                },
                {
                    "name": "ESSArch_Core.tasks.ValidateXMLFile",
                    "if": generate_premis,
                    "label": "Validate premis",
                    "params": {
                        "xml_filename": "{{_PREMIS_PATH}}",
                    }
                },
                {
                    "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                    "label": "Diff-check against content-mets",
                    "args": ["{{_OBJPATH}}", "{{_CONTENT_METS_PATH}}"],
                },
                {
                    "name": "ESSArch_Core.tasks.CompareXMLFiles",
                    "if": generate_premis,
                    "label": "Compare premis and content-mets",
                    "args": ["{{_PREMIS_PATH}}", "{{_CONTENT_METS_PATH}}"],
                    "params": {'recursive': False},
                },
                {
                    "name": "ESSArch_Core.tasks.CompareRepresentationXMLFiles",
                    "if": has_representations and generate_premis,
                    "label": "Compare representation premis and mets",
                }
            ]
        },
        {
            "name": "ESSArch_Core.tasks.UpdateIPSizeAndCount",
            "label": "Update IP size and file count",
        },
    ]

    workflow += new_ip.create_preservation_workflow()
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

    class Meta(MaintenanceJob.Meta):
        permissions = (
            ('run_conversionjob', 'Can run conversion job'),
        )

    def preview(self, ip: InformationPackage):
        storage_obj = ip.storage.readable().fastest().first()
        if storage_obj is None:
            raise NoReadableStorage

        for pattern, _ in self.specification.items():
            yield from storage_obj.list_files(pattern, case_sensitive=False)

    def create_notification(self, status):
        if self.user is None:
            return

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

    def convert(self, ip, path, rootpath, tool: ConversionTool, options, new_ip):
        relpath = PurePath(path).relative_to(rootpath).as_posix()
        entry = ConversionJobEntry.objects.create(
            job=self,
            start_date=timezone.now(),
            ip=ip,
            old_document=relpath,
            tool=tool.name,
        )
        tool.run(path, rootpath, options)
        os.remove(path)

        entry.end_date = timezone.now()
        entry.save()

        EventIP.objects.create(
            eventType=self.delete_event_type,
            eventOutcome=EventIP.SUCCESS,
            eventOutcomeDetailNote='Converted {}'.format(relpath),
            linkingObjectIdentifierValue=new_ip.object_identifier_value,
        )

        return entry

    @transaction.atomic
    def _run(self):
        self.delete_event_type = EventType.objects.get(eventType=50750)

        ips = self.information_packages
        tmpdir = Path.objects.get(entity='temp').value

        for ip in ips.iterator():
            storage_obj: Optional[StorageObject] = ip.storage.readable().fastest().first()
            if storage_obj is None:
                raise NoReadableStorage

            new_ip = ip.create_new_generation(ip.state, ip.responsible, None)
            new_ip_tmpdir = os.path.join(tmpdir, new_ip.object_identifier_value)
            storage_obj.read(new_ip_tmpdir, None, extract=True)
            new_ip.object_path = new_ip_tmpdir
            new_ip.save()

            # convert files specified in rule
            for pattern, spec in self.specification.items():
                tool = ConversionTool.objects.get(name=spec['tool'])
                options = spec['options']

                for path in iglob(new_ip_tmpdir + '/' + pattern, case_sensitive=False):
                    if not in_directory(path, new_ip_tmpdir):
                        raise ValueError('Invalid file-pattern accessing files outside of package')

                    if os.path.isdir(path):
                        for root, _dirs, files in walk(path):
                            for f in files:
                                fpath = os.path.join(root, f)
                                self.convert(ip, fpath, new_ip_tmpdir, tool, options, new_ip)
                    else:
                        self.convert(ip, path, new_ip_tmpdir, tool, options, new_ip)

            with allow_join_result():
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
