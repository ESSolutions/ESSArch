import errno
import os
import shutil
import tarfile
import uuid

from collections import OrderedDict

from celery import states as celery_states
from celery.result import allow_join_result

from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone

from elasticsearch_dsl import Search, Q as ElasticQ

from glob2 import iglob

import jsonfield

from lxml import etree

from scandir import walk

import six

from weasyprint import HTML

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.essxml.util import get_agents
from ESSArch_Core.fixity.checksum import calculate_checksum
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.profiles.models import ProfileIP
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.search.ingest import index_path
from ESSArch_Core.WorkflowEngine.models import ProcessTask
from ESSArch_Core.util import (
    convert_file,
    creation_date,
    find_destination,
    timestamp_to_datetime,
)

ARCHIVAL_OBJECT = 'archival_object'
METADATA = 'metadata'
TYPE_CHOICES = (
    (ARCHIVAL_OBJECT, 'Archival Object'),
    (METADATA, 'Metadata'),
)

class AppraisalRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=100, choices=TYPE_CHOICES, default=ARCHIVAL_OBJECT)
    information_packages = models.ManyToManyField('ip.InformationPackage', related_name='appraisal_rules')
    frequency = models.CharField(max_length=255, blank=True, default='')  # cron syntax, blank for manual only appraisal
    specification = jsonfield.JSONField(null=True, default=None)  # empty for all files in IP or all fields in tree node


class AppraisalJob(models.Model):
    STATUS_CHOICES = zip(
        celery_states.ALL_STATES, celery_states.ALL_STATES
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey('maintenance.AppraisalRule', on_delete=models.CASCADE, null=True, related_name='jobs')
    status = models.CharField(choices=STATUS_CHOICES, max_length=50, default=celery_states.PENDING)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)

    def _generate_report(self):
        template = 'appraisal_report.html'
        dstdir = Path.objects.get(entity='appraisal_reports').value
        dst = os.path.join(dstdir, '%s.pdf' % self.pk)

        render = render_to_string(template, {'job': self, 'rule': self.rule})
        HTML(string=render).write_pdf(dst)

    def _mark_as_complete(self):
        self.status = celery_states.SUCCESS
        self.end_date = timezone.now()
        self.save()
        self._generate_report()

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

        if not ips.exists():
            self._mark_as_complete()

        for ip in ips.iterator():
            if ip.cached == False:
                with allow_join_result():
                    t, created = ProcessTask.objects.get_or_create(
                        name='workflow.tasks.CacheAIP',
                        params={'aip': str(ip.pk)},
                        information_package_id=str(ip.pk),
                        defaults={'responsible': ip.responsible, 'eager': False}
                    )

                    if not created:
                        t.run()

                continue

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

                mets_tree = etree.parse(mets_path)
                agents = get_agents(mets_tree.getroot())

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

                    premis_profile_data['_AGENTS'] = agents
                    filesToCreate[premis_path] = {
                        'spec': premis_profile.specification,
                        'data': fill_specification_data(premis_profile_data, ip=new_ip, sa=sa),
                    }

                aip_profile_data['_AGENTS'] = agents
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
                info['_AGENTS'] = agents

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
                    params={'ip': str(new_ip.pk)},
                    information_package=new_ip,
                    responsible=new_ip.responsible,
                ).run().get()

                t = ProcessTask.objects.create(
                    name='workflow.tasks.StoreAIP',
                    params={'aip': str(new_ip.pk)},
                    information_package_id=str(new_ip.pk),
                    responsible=new_ip.responsible,
                )

                t.run()

            ips = get_information_packages(self)
            if not ips.exists():
                self._mark_as_complete()


    def run(self):
        if self.rule.type == ARCHIVAL_OBJECT:
            return self._run_archive_object()

        return self._run_metadata()

    class Meta:
        get_latest_by = 'start_date'


class AppraisalJobEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey('maintenance.AppraisalJob', on_delete=models.CASCADE, related_name='entries')
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)

    # when type of rule is ARCHIVAL_OBJECT
    ip = models.ForeignKey('ip.InformationPackage', on_delete=models.SET_NULL, null=True, related_name='appraisal_job_entries')
    document = models.CharField(max_length=255, blank=True)

    # when type of rule is METADATA
    component = models.CharField(max_length=255, blank=True)
    component_field = models.CharField(max_length=255, blank=True)


class ConversionRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    information_packages = models.ManyToManyField('ip.InformationPackage', related_name='conversion_rules')
    frequency = models.CharField(max_length=255, blank=True, default='')  # cron syntax, blank for manual only appraisal
    specification = jsonfield.JSONField(null=True, default=None)


class ConversionJob(models.Model):
    STATUS_CHOICES = zip(
        celery_states.ALL_STATES, celery_states.ALL_STATES
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey('maintenance.ConversionRule', on_delete=models.CASCADE, null=True, related_name='jobs')
    status = models.CharField(choices=STATUS_CHOICES, max_length=50, default=celery_states.PENDING)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)

    class Meta:
        get_latest_by = 'start_date'

    def _generate_report(self):
        template = 'conversion_report.html'
        dstdir = Path.objects.get(entity='conversion_reports').value
        dst = os.path.join(dstdir, '%s.pdf' % self.pk)

        render = render_to_string(template, {'job': self, 'rule': self.rule})
        HTML(string=render).write_pdf(dst)

    def _mark_as_complete(self):
        self.status = celery_states.SUCCESS
        self.end_date = timezone.now()
        self.save()
        self._generate_report()

    def run(self):
        def get_information_packages(job):
            return self.rule.information_packages.filter(
                active=True,
            ).exclude(
                conversion_job_entries__job=self,
            )

        ips = get_information_packages(self)

        if not ips.exists():
            self._mark_as_complete()

        for ip in ips.iterator():
            if ip.cached == False:
                with allow_join_result():
                    t, created = ProcessTask.objects.get_or_create(
                        name='workflow.tasks.CacheAIP',
                        params={'aip': str(ip.pk)},
                        information_package_id=str(ip.pk),
                        defaults={'responsible': ip.responsible, 'eager': False}
                    )

                    if not created:
                        t.run()

                continue

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

            mets_tree = etree.parse(mets_path)
            agents = get_agents(mets_tree.getroot())

            # copy files to new generation
            shutil.copytree(srcdir, dstdir)

            # convert files specified in rule
            for pattern, spec in six.iteritems(self.rule.specification):
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

                premis_profile_data['_AGENTS'] = agents
                filesToCreate[premis_path] = {
                    'spec': premis_profile.specification,
                    'data': fill_specification_data(premis_profile_data, ip=new_ip, sa=sa),
                }

            aip_profile_data['_AGENTS'] = agents
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
            info['_AGENTS'] = agents

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
                params={'ip': str(new_ip.pk)},
                information_package=new_ip,
                responsible=new_ip.responsible,
            ).run().get()

            t = ProcessTask.objects.create(
                name='workflow.tasks.StoreAIP',
                params={'aip': str(new_ip.pk)},
                information_package_id=str(new_ip.pk),
                responsible=new_ip.responsible,
            )

            t.run()

            ips = get_information_packages(self)
            if not ips.exists():
                self._mark_as_complete()


class ConversionJobEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey('maintenance.ConversionJob', on_delete=models.CASCADE, related_name='entries')
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)

    ip = models.ForeignKey('ip.InformationPackage', on_delete=models.SET_NULL, null=True, related_name='conversion_job_entries')
    old_document = models.CharField(max_length=255, blank=True)
    new_document = models.CharField(max_length=255, blank=True)
    tool = models.CharField(max_length=255, blank=True)
