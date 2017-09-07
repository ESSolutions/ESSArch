"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Core
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

from __future__ import division

import datetime
import mimetypes
import os
import re
import tarfile
import zipfile

from operator import itemgetter

from celery import states as celery_states

from django.db import models

from rest_framework import exceptions, filters, permissions, status
from rest_framework.response import Response

from ESSArch_Core.configuration.models import ArchivePolicy, Path

from ESSArch_Core.profiles.models import (
    SubmissionAgreement as SA,
    ProfileIP, ProfileSA,
)

from ESSArch_Core.util import (
    generate_file_response,
    get_files_and_dirs,
    get_tree_size_and_count,
    in_directory,
    timestamp_to_datetime,
)

import math
import uuid

MESSAGE_DIGEST_ALGORITHM_CHOICES = (
    (ArchivePolicy.MD5, 'MD5'),
    (ArchivePolicy.SHA1, 'SHA-1'),
    (ArchivePolicy.SHA224, 'SHA-224'),
    (ArchivePolicy.SHA256, 'SHA-256'),
    (ArchivePolicy.SHA384, 'SHA-384'),
    (ArchivePolicy.SHA512, 'SHA-512'),
)


class ArchivalInstitution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name = 'ArchivalInstitution'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.name, self.id)


class ArchivistOrganization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name = 'ArchivistOrganization'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.name, self.id)


class ArchivalType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name = 'ArchivalType'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.name, self.id)


class ArchivalLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name = 'ArchivalLocation'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.name, self.id)


class InformationPackage(models.Model):
    """
    Informaion Package
    """

    SIP = 0
    AIC = 1
    AIP = 2
    AIU = 3
    DIP = 4

    PACKAGE_TYPE_CHOICES = (
        (SIP, 'SIP'),
        (AIC, 'AIC'),
        (AIP, 'AIP'),
        (AIU, 'AIU'),
        (DIP, 'DIP'),
    )

    PRESERVATION_LEVEL_VALUE_CHOICES = (
        (1, 'full'),
    )

    INFORMATION_CLASS_CHOICES = (
        (0, '0'),
        (1, '1'),
        (2, '2'),
        (3, '3'),
        (4, '4'),
    )

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    object_identifier_value = models.CharField(max_length=255, unique=True)
    label = models.CharField(max_length=255, blank=True)
    content = models.CharField(max_length=255)
    create_date = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=255)

    object_path = models.CharField(max_length=255, blank=True)
    object_size = models.BigIntegerField(default=0)
    object_num_items = models.IntegerField(default=0)

    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)

    message_digest_algorithm = models.IntegerField(null=True, choices=MESSAGE_DIGEST_ALGORITHM_CHOICES)
    message_digest = models.CharField(max_length=128, blank=True)
    active = models.BooleanField(default=True)

    linking_agent_identifier_value = models.CharField(max_length=255, blank=True)
    create_agent_identifier_value = models.CharField(max_length=255, blank=True)

    entry_date = models.DateTimeField(null=True)
    entry_agent_identifier_value = models.CharField(max_length=255, blank=True)

    package_type = models.IntegerField(null=True, choices=PACKAGE_TYPE_CHOICES)
    preservation_level_value = models.IntegerField(choices=PRESERVATION_LEVEL_VALUE_CHOICES, default=1)

    delivery_type = models.CharField(max_length=255, blank=True)
    information_class = models.IntegerField(null=True, choices=INFORMATION_CLASS_CHOICES)
    generation = models.IntegerField(null=True)

    cached = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)

    last_changed_local = models.DateTimeField(null=True)
    last_changed_external = models.DateTimeField(null=True)

    responsible = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL,
        related_name='information_packages', null=True
    )

    policy = models.ForeignKey('configuration.ArchivePolicy', on_delete=models.PROTECT, related_name='information_packages', null=True)
    aic = models.ForeignKey('self', on_delete=models.PROTECT, related_name='information_packages', null=True)

    submission_agreement = models.ForeignKey(
        SA,
        on_delete=models.CASCADE,
        related_name='information_packages',
        default=None,
        null=True,
    )
    submission_agreement_locked = models.BooleanField(default=False)
    archival_institution = models.ForeignKey(
        ArchivalInstitution,
        on_delete=models.CASCADE,
        related_name='information_packages',
        default=None,
        null=True
    )
    archivist_organization = models.ForeignKey(
        ArchivistOrganization,
        on_delete=models.CASCADE,
        related_name='information_packages',
        default=None,
        null=True
    )
    archival_type = models.ForeignKey(
        ArchivalType,
        on_delete=models.CASCADE,
        related_name='information_packages',
        default=None,
        null=True
    )
    archival_location = models.ForeignKey(
        ArchivalLocation,
        on_delete=models.CASCADE,
        related_name='information_packages',
        default=None,
        null=True
    )

    def related_ips(self):
        sorting = ('generation', 'package_type', 'create_date',)

        if self.package_type == InformationPackage.AIC:
            return self.information_packages.order_by(*sorting)

        return InformationPackage.objects.filter(
            aic__isnull=False, aic=self.aic,
        ).exclude(pk=self.pk).order_by(*sorting)

    def save(self, *args, **kwargs):
        if not self.object_identifier_value:
            self.object_identifier_value = str(self.pk)

        super(InformationPackage, self).save(*args, **kwargs)

    def check_db_sync(self):
        if self.last_changed_local is not None and self.last_changed_external is not None:
            return (self.last_changed_local-self.last_changed_external).total_seconds() == 0

    def get_profile_rel(self, profile_type):
        return self.profileip_set.get(
            profile__profile_type=profile_type
        )

    def profile_locked(self, profile_type):
        try:
            rel = self.get_profile_rel(profile_type)
            return rel.LockedBy is not None
        except ProfileIP.DoesNotExist:
            return False

    def get_profile(self, profile_type):
        if self.submission_agreement is None:
            return None

        try:
            return getattr(self.submission_agreement, 'profile_%s' % profile_type)
        except AttributeError:
            raise AttributeError('No such profile type')

    def get_profile_data(self, profile_type):
        return self.get_profile_rel(profile_type).data.data

    def unlock_profile(self, ptype):
        ProfileIP.objects.filter(
            ip=self, profile__profile_type=ptype
        ).update(LockedBy=None)

        self.state = 'Preparing'
        self.save(update_fields=['state'])

    def get_container_format(self):
        try:
            return self.get_profile_data('transfer_project').get(
                'container_format', 'tar'
            )
        except:
            return 'tar'

    def get_checksum_algorithm(self):
        try:
            name = self.get_profile_data('transfer_project').get(
                'checksum_algorithm', 'SHA-256'
            )
        except:
            name = 'SHA-256'

        return name

    def get_email_recipient(self):
        try:
            return self.get_profile_data('transfer_project').get(
                'preservation_organization_receiver_email'
            )
        except:
            return None

    @property
    def step_state(self):
        """
        Gets the state of the IP based on its steps

        Args:

        Returns:
            Can be one of the following:
            SUCCESS, STARTED, FAILURE, PENDING

            Which is decided by five scenarios:

            * If there are no steps, then PENDING.
            * If there are steps and they are all pending,
              then PENDING.
            * If a step has started, then STARTED.
            * If a step has failed, then FAILURE.
            * If all steps have succeeded, then SUCCESS.
        """

        steps = self.steps.all()
        state = celery_states.SUCCESS

        if not steps:
            return celery_states.PENDING

        for step in steps:
            step_status = step.status

            if step_status == celery_states.STARTED:
                state = step_status
            if (step_status == celery_states.PENDING and
                    state != celery_states.STARTED):
                state = step_status
            if step_status == celery_states.FAILURE:
                return step_status

        return state

    def status(self):
        if self.state in ["Prepared", "Uploaded", "Created", "Submitted", "Received", "Transferred", 'Archived']:
            return 100

        if self.state == "Preparing":
            if not self.submission_agreement_locked:
                return 33

            progress = 66

            try:
                sa_profiles = ProfileSA.objects.filter(
                    submission_agreement=self.submission_agreement
                )

                ip_profiles_locked = ProfileIP.objects.filter(
                    ip=self, LockedBy__isnull=False,
                    profile__profile_type__in=sa_profiles.values(
                        "profile__profile_type"
                    )
                )

                progress += math.ceil(ip_profiles_locked.count() * ((100-progress) / sa_profiles.count()))

            except ZeroDivisionError:
                pass

            return progress

        steps = self.steps.all()

        if steps:
            try:
                progress = sum([s.progress for s in steps])
                return progress / len(steps)
            except:
                return 0

        return 0

    def files(self, path='', force_download=False):
        mimetypes.suffix_map = {}
        mimetypes.encodings_map = {}
        mimetypes.types_map = {}
        mimetypes.common_types = {}
        mimetypes_file = Path.objects.get(
            entity="path_mimetypes_definitionfile"
        ).value
        mimetypes.init(files=[mimetypes_file])
        mtypes = mimetypes.types_map

        MAX_FILE_SIZE = 100000000 # 100 MB

        if os.path.isfile(self.object_path):
            container = self.object_path
            xml = os.path.splitext(self.object_path)[0] + '.xml'

            if path.startswith(os.path.basename(container)):
                fullpath = os.path.join(os.path.dirname(container), path)

                if tarfile.is_tarfile(container):
                    with tarfile.open(container) as tar:
                        if fullpath == container:
                            entries = []
                            for member in tar.getmembers():
                                if not member.isfile():
                                    continue

                                entries.append({
                                    "name": member.name,
                                    "type": 'file',
                                    "size": member.size,
                                    "modified": timestamp_to_datetime(member.mtime),
                                })
                            return Response(entries)
                        else:
                            subpath = fullpath[len(container)+1:]
                            try:
                                member = tar.getmember(subpath)

                                if not member.isfile():
                                    raise exceptions.NotFound

                                f = tar.extractfile(member)
                                content_type = mtypes.get(os.path.splitext(subpath)[1])
                                return generate_file_response(f, content_type, force_download)
                            except KeyError:
                                raise exceptions.NotFound

                elif zipfile.is_zipfile(container):
                    with zipfile.ZipFile(container) as zipf:
                        if fullpath == container:
                            entries = []
                            for member in zipf.filelist:
                                if member.filename.endswith('/'):
                                    continue

                                entries.append({
                                    "name": member.filename,
                                    "type": 'file',
                                    "size": member.file_size,
                                    "modified": datetime.datetime(*member.date_time),
                                })
                            return Response(entries)
                        else:
                            subpath = fullpath[len(container)+1:]
                            try:
                                f = zipf.open(subpath)
                                content_type = mtypes.get(os.path.splitext(subpath)[1])
                                return generate_file_response(f, content_type, force_download)
                            except KeyError:
                                raise exceptions.NotFound


                content_type = mtypes.get(os.path.splitext(fullpath)[1])
                return generate_file_response(open(fullpath), content_type, force_download)
            elif os.path.isfile(xml) and path == os.path.basename(xml):
                fullpath = os.path.join(os.path.dirname(container), path)
                content_type = mtypes.get(os.path.splitext(fullpath)[1])
                return generate_file_response(open(fullpath), content_type, force_download)
            elif path == '':
                entries = []

                entries.append({
                    "name": os.path.basename(container),
                    "type": 'file',
                    "size": os.path.getsize(container),
                    "modified": timestamp_to_datetime(os.path.getmtime(container)),
                })

                if os.path.isfile(xml):
                    entries.append({
                        "name": os.path.basename(xml),
                        "type": 'file',
                        "size": os.path.getsize(xml),
                        "modified": timestamp_to_datetime(os.path.getmtime(xml)),
                    })
                return Response(entries)

            elif path is not None:
                raise exceptions.NotFound

        entries = []
        fullpath = os.path.join(self.object_path, path)

        if not in_directory(fullpath, self.object_path):
            raise exceptions.ParseError('Illegal path %s' % path)

        if not os.path.exists(fullpath):
            raise exceptions.NotFound

        if os.path.isfile(fullpath):
            content_type = mtypes.get(os.path.splitext(fullpath)[1])
            return generate_file_response(open(fullpath), content_type, force_download)

        for entry in get_files_and_dirs(fullpath):
            entry_type = "dir" if entry.is_dir() else "file"

            if entry_type == 'file' and re.search(r'\_\d+$', entry.name) is not None:  # file chunk
                continue

            size, _ = get_tree_size_and_count(entry.path)

            entries.append(
                {
                    "name": os.path.basename(entry.path),
                    "type": entry_type,
                    "size": size,
                    "modified": timestamp_to_datetime(entry.stat().st_mtime),
                }
            )

        sorted_entries = sorted(entries, key=itemgetter('name'))
        return Response(sorted_entries)


    def delete(self, *args, **kwargs):
        super(InformationPackage, self).delete(*args, **kwargs)
        ArchivalInstitution.objects.filter(
            information_packages__isnull=True
        ).delete()
        ArchivistOrganization.objects.filter(
            information_packages__isnull=True
        ).delete()
        ArchivalType.objects.filter(
            information_packages__isnull=True
        ).delete()
        ArchivalLocation.objects.filter(
            information_packages__isnull=True
        ).delete()

    class Meta:
        ordering = ["id"]
        verbose_name = 'Information Package'
        permissions = (
            ('can_upload', 'Can upload files to IP'),
            ('set_uploaded', 'Can set IP as uploaded'),
            ('create_sip', 'Can create SIP'),
            ('submit_sip', 'Can submit SIP'),
            ('transfer_sip', 'Can transfer SIP'),
            ('change_sa', 'Can change SA connected to IP'),
            ('lock_sa', 'Can lock SA to IP'),
            ('unlock_profile', 'Can unlock profile connected to IP'),
            ('can_receive_remote_files', 'Can receive remote files'),
            ('receive', 'Can receive IP'),
            ('preserve', 'Can preserve IP'),
            ('get_from_storage', 'Can get extracted IP from storage'),
            ('get_tar_from_storage', 'Can get packaged IP from storage'),
            ('get_from_storage_as_new', 'Can get IP "as new" from storage'),
            ('add_to_ingest_workarea', 'Can add IP to ingest workarea'),
            ('add_to_ingest_workarea_as_tar', 'Can add IP as tar to ingest workarea'),
            ('add_to_ingest_workarea_as_new', 'Can add IP as new generation to ingest workarea'),
            ('diff-check', 'Can diff-check IP'),
            ('query', 'Can query IP'),
        )

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.label, self.pk)

    def get_value_array(self):
        # make an associative array of all fields  mapping the field
        # name to the current value of the field
        return {
            field.name: field.value_to_string(self)
            for field in InformationPackage._meta.fields
        }


class InformationPackageMetadata(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip = models.ForeignKey(InformationPackage, on_delete=models.PROTECT)
    type = models.IntegerField(null=True)
    server = models.IntegerField(null=True)
    server_url = models.CharField(max_length=255, blank=True)
    local_path = models.CharField(max_length=255, blank=True)
    blob = models.TextField(blank=True)

    message_digest_algorithm = models.IntegerField(null=True, choices=MESSAGE_DIGEST_ALGORITHM_CHOICES)
    message_digest = models.CharField(max_length=128, blank=True)

    last_changed_local = models.DateTimeField(null=True)
    last_changed_external = models.DateTimeField(null=True)

    def check_db_sync(self):
        if self.last_changed_local is not None and self.last_changed_external is not None:
            return (self.last_changed_local-self.last_changed_external).total_seconds() == 0


class EventIP(models.Model):
    """
    Events related to IP
    """

    OUTCOME_CHOICES = (
        (10, 'debug'),
        (20, 'info'),
        (30, 'warning'),
        (40, 'error'),
        (50, 'critical'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    eventType = models.ForeignKey(
        'configuration.EventType',
        on_delete=models.CASCADE
    )
    eventDateTime = models.DateTimeField(auto_now_add=True)
    task = models.ForeignKey(
        'WorkflowEngine.ProcessTask', on_delete=models.CASCADE, null=True,
        related_name='events',
    ) # The task that generated the event
    application = models.CharField(max_length=255)
    eventVersion = models.CharField(max_length=255) # The version number of the application (from versioneer)
    eventOutcome = models.IntegerField(choices=OUTCOME_CHOICES, null=True, default=None) # Success (0) or Fail (1)
    eventOutcomeDetailNote = models.CharField(max_length=1024) # Result or traceback from IP
    linkingAgentIdentifierValue = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL,
        related_name='events', null=True
    )
    linkingObjectIdentifierValue = models.ForeignKey(
        'InformationPackage',
        on_delete=models.CASCADE,
        related_name='events',
        null=True,
    )

    class Meta:
        ordering = ["eventType"]
        verbose_name = 'Events related to IP'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s (%s)' % (self.eventType.eventDetail, self.id)

    def get_value_array(self):
        # make an associative array of all fields  mapping the field
        # name to the current value of the field
        return {
            field.name: field.value_to_string(self)
            for field in EventIP._meta.fields
        }


class Workarea(models.Model):
    INGEST = 0
    ACCESS = 1
    TYPE_CHOICES = (
        (INGEST, 'Ingest'),
        (ACCESS, 'Access'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    ip = models.ForeignKey('ip.InformationPackage', on_delete=models.CASCADE, related_name='workareas')
    read_only = models.BooleanField(default=True)
    type = models.IntegerField(choices=TYPE_CHOICES, default=0)

    @property
    def path(self):
        area_dir = Path.objects.get(entity=self.get_type_display() + '_workarea').value
        return os.path.join(area_dir, self.user.username, self.ip.object_identifier_value)

    class Meta:
        permissions = (
            ('move_from_ingest_workarea', 'Can move IP from ingest workarea'),
            ('move_from_access_workarea', 'Can move IP from access workarea'),
            ('preserve_from_ingest_workarea', 'Can preserve IP from ingest workarea'),
            ('preserve_from_access_workarea', 'Can preserve IP from access workarea'),
        )


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=255)
    responsible = models.ForeignKey('auth.User', on_delete=models.PROTECT)
    information_packages = models.ManyToManyField('ip.InformationPackage', related_name='orders', blank=True)

    class Meta:
        permissions = (
            ('prepare_order', 'Can prepare order'),
        )
