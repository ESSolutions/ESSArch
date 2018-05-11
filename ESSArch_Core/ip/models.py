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

import math
import os
import uuid
from copy import deepcopy

import jsonfield
import six
from celery import states as celery_states
from django.conf import settings
from django.db import models, transaction
from django.db.models import Max, Min, Q, Subquery
from django.utils.encoding import python_2_unicode_compatible
from groups_manager.utils import get_permission_name
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import assign_perm
from rest_framework import exceptions
from rest_framework.response import Response

from ESSArch_Core.auth.models import Member
from ESSArch_Core.auth.util import get_membership_descendants
from ESSArch_Core.configuration.models import ArchivePolicy, Path
from ESSArch_Core.profiles.models import ProfileIP, ProfileIPData, ProfileSA
from ESSArch_Core.profiles.models import SubmissionAgreement as SA
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.util import in_directory, list_files, timestamp_to_datetime

MESSAGE_DIGEST_ALGORITHM_CHOICES = (
    (ArchivePolicy.MD5, 'MD5'),
    (ArchivePolicy.SHA1, 'SHA-1'),
    (ArchivePolicy.SHA224, 'SHA-224'),
    (ArchivePolicy.SHA256, 'SHA-256'),
    (ArchivePolicy.SHA384, 'SHA-384'),
    (ArchivePolicy.SHA512, 'SHA-512'),
)
MESSAGE_DIGEST_ALGORITHM_CHOICES_DICT = {v: k for k, v in MESSAGE_DIGEST_ALGORITHM_CHOICES}


@python_2_unicode_compatible
class ArchivalInstitution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=16, unique=True, blank=True, null=True)  # ISO 15511
    country_code = models.CharField(max_length=3, blank=True)

    class Meta:
        verbose_name = 'ArchivalInstitution'

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class ArchivistOrganization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=255, unique=True, blank=True, null=True)

    class Meta:
        verbose_name = 'ArchivistOrganization'

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class ArchivalType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name = 'ArchivalType'

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class ArchivalLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name = 'ArchivalLocation'

    def __str__(self):
        return self.name


class InformationPackageManager(models.Manager):
    def for_user(self, user, perms):
        """
        Returns information packages for which a given ``users`` groups in the
        ``users`` current organization has all permissions in ``perms``

        :param user: ``User`` instance for which information packages would be
        returned
        :param perms: single permission string, or sequence of permission
        strings which should be checked
        """

        if user.is_superuser:
            return self.get_queryset()

        if isinstance(perms, six.string_types):
            perms = [perms]

        groups = get_membership_descendants(user.user_profile.current_organization, user)
        django_groups = [g.django_group for g in groups]

        group_sub = InformationPackageGroupObjectPermission.objects.filter(
            group__in=django_groups, permission__codename__in=perms)

        user_sub = InformationPackageUserObjectPermission.objects.filter(
            user=user, permission__codename__in=perms)

        return self.get_queryset().filter(
            Q(pk__in=Subquery(group_sub.values('content_object'))) |
            Q(pk__in=Subquery(user_sub.values('content_object')))
        )

    def visible_to_user(self, user):
        return self.for_user(user, 'view_informationpackage')


@python_2_unicode_compatible
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

    appraisal_date = models.DateTimeField(null=True)

    message_digest_algorithm = models.IntegerField(null=True, choices=MESSAGE_DIGEST_ALGORITHM_CHOICES)
    message_digest = models.CharField(max_length=128, blank=True)
    active = models.BooleanField(default=True)

    content_mets_path = models.CharField(max_length=255, blank=True)
    content_mets_create_date = models.DateTimeField(null=True)
    content_mets_size = models.BigIntegerField(null=True)
    content_mets_digest_algorithm = models.IntegerField(null=True, choices=MESSAGE_DIGEST_ALGORITHM_CHOICES)
    content_mets_digest = models.CharField(max_length=128, blank=True)

    package_mets_path = models.CharField(max_length=255, blank=True)
    package_mets_create_date = models.DateTimeField(null=True)
    package_mets_size = models.BigIntegerField(null=True)
    package_mets_digest_algorithm = models.IntegerField(null=True, choices=MESSAGE_DIGEST_ALGORITHM_CHOICES)
    package_mets_digest = models.CharField(max_length=128, blank=True)

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

    tag = models.ForeignKey('tags.TagStructure', on_delete=models.SET_NULL, related_name='information_packages', null=True)

    submission_agreement = models.ForeignKey(SA, on_delete=models.PROTECT, related_name='information_packages',
                                             default=None, null=True)
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

    objects = InformationPackageManager()

    def save(self, *args, **kwargs):
        if not self.object_identifier_value:
            self.object_identifier_value = str(self.pk)

        super(InformationPackage, self).save(*args, **kwargs)

    def is_first_generation(self):
        if self.aic is None:
            return True

        min_generation = InformationPackage.objects.filter(aic=self.aic) \
                                                    .exclude(workareas__read_only=False) \
                                                    .aggregate(Min('generation'))['generation__min']
        return self.generation == min_generation

    def is_last_generation(self):
        if self.aic is None:
            return True

        max_generation = InformationPackage.objects.filter(aic=self.aic) \
                                                    .exclude(workareas__read_only=False) \
                                                    .aggregate(Max('generation'))['generation__max']
        return self.generation == max_generation

    def create_new_generation(self, state, responsible, object_identifier_value):
        try:
            perms = deepcopy(settings.IP_CREATION_PERMS_MAP)
        except AttributeError:
            raise exceptions.ParseError('Missing IP_CREATION_PERMS_MAP in settings')

        new_aip = deepcopy(self)
        new_aip.pk = None
        new_aip.active = True
        new_aip.object_identifier_value = None
        new_aip.state = state
        new_aip.cached = False
        new_aip.archived = False
        new_aip.object_path = ''
        new_aip.responsible = responsible

        with transaction.atomic():
            max_generation = InformationPackage.objects.select_for_update().filter(aic=self.aic).aggregate(Max('generation'))['generation__max']
            new_aip.generation = max_generation + 1
            new_aip.save()

        new_aip.object_identifier_value = object_identifier_value if object_identifier_value is not None else str(new_aip.pk)
        new_aip.save(update_fields=['object_identifier_value'])

        for profile_ip in self.profileip_set.all():
            new_profile_ip = deepcopy(profile_ip)
            new_profile_ip.pk = None
            new_profile_ip.ip = new_aip
            new_profile_ip.save()

        member = Member.objects.get(django_user=responsible)
        user_perms = perms.pop('owner', [])

        organization = responsible.user_profile.current_organization
        organization.assign_object(new_aip, custom_permissions=perms)

        for perm in user_perms:
            perm_name = get_permission_name(perm, new_aip)
            assign_perm(perm_name, member.django_user, new_aip)

        return new_aip

    def check_db_sync(self):
        if self.last_changed_local is not None and self.last_changed_external is not None:
            return (self.last_changed_local-self.last_changed_external).total_seconds() == 0

    def new_version_in_progress(self):
        ip = self.related_ips(cached=False).filter(workareas__read_only=False).first()

        if ip is not None:
            return ip.workareas.first()

        return None

    def create_profile_rels(self, profile_types, user):
        sa = self.submission_agreement
        extra_data = fill_specification_data(ip=self, sa=sa)
        for p_type in profile_types:
            profile = getattr(sa, 'profile_%s' % p_type, None)

            if profile is None:
                continue

            profile_ip = ProfileIP.objects.create(ip=self, profile=profile)
            data = {}

            for field in profile_ip.profile.template:
                try:
                    if field['defaultValue'] in extra_data:
                        data[field['key']] = extra_data[field['defaultValue']]
                        continue

                    data[field['key']] = field['defaultValue']
                except KeyError:
                    pass
            data_obj = ProfileIPData.objects.create(relation=profile_ip, data=data, version=0, user=user)
            profile_ip.data = data_obj
            profile_ip.save()


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
        try:
            profile_rel = self.get_profile_rel(profile_type)
        except ProfileIP.DoesNotExist:
            return {}

        if profile_rel.data is None:
            return {}

        data = profile_rel.data.data
        data.update(self.get_profile_rel(profile_type).get_related_profile_data(original_keys=True))
        return data

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
            if self.profile_type == InformationPackage.SIP:
                name = self.get_profile_data('transfer_project').get(
                    'checksum_algorithm', 'SHA-256'
                )
            else:
                name = self.policy.get_checksum_algorithm_display().upper()
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

    def get_events_file_path(self):
        if os.path.isdir(self.object_path):
            return os.path.join(self.object_path, 'ipevents.xml')

        return os.path.splitext(self.object_path)[0] + '_ipevents.xml'

    def related_ips(self, cached=True):
        if self.package_type == InformationPackage.AIC:
            if not cached:
                return InformationPackage.objects.filter(aic=self)

            return self.information_packages.all()

        if self.aic is not None:
            if not cached:
                return InformationPackage.objects.filter(aic=self.aic).exclude(pk=self.pk)

            if 'information_packages' in self.aic._prefetched_objects_cache:
                # prefetched, don't need to filter
                return self.aic.information_packages
            else:
                return self.aic.information_packages.exclude(pk=self.pk)

        return InformationPackage.objects.none()

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

            If the IP is an AIC, then the same algorithm is
            applied on the related IPs instead
        """

        if self.package_type == InformationPackage.AIC:
            ips = self.related_ips()
            state = celery_states.SUCCESS

            for ip in ips:
                ip_step_state = ip.step_state

                if ip_step_state == celery_states.STARTED:
                    state = ip_step_state
                if (ip_step_state == celery_states.PENDING and
                            state != celery_states.STARTED):
                    state = ip_step_state
                if ip_step_state == celery_states.FAILURE:
                    return ip_step_state

            return state

        steps = self.steps.all()
        state = celery_states.SUCCESS

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

    def files(self, path='', force_download=False, paginator=None, request=None):
        if self.archived:
            storage_obj = self.storage.readable().fastest().first()
            if storage_obj is None:
                raise ValueError("No readable storage configured for IP")
            fp = storage_obj.read(path)
            path = os.path.realpath(fp.name)
            return list_files(path, force_download, paginator=paginator, request=request)

        if os.path.isfile(self.object_path):
            if len(path):
                fullpath = os.path.join(os.path.dirname(self.object_path), path)
                return list_files(fullpath, force_download, paginator=paginator, request=request)

            container = self.object_path
            xml = os.path.splitext(container)[0] + '.xml'

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

        fullpath = os.path.join(self.object_path, path)

        if not in_directory(fullpath, self.object_path):
            raise exceptions.ParseError('Illegal path %s' % path)

        return list_files(fullpath, force_download, paginator=paginator, request=request)


    class Meta:
        ordering = ["generation", "-create_date"]
        verbose_name = 'Information Package'
        permissions = (
            ('view_informationpackage', 'Can view IP'),
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
            ('preserve_dip', 'Can preserve DIP'),
            ('get_from_storage', 'Can get extracted IP from storage'),
            ('get_tar_from_storage', 'Can get packaged IP from storage'),
            ('get_from_storage_as_new', 'Can get IP "as new" from storage'),
            ('add_to_ingest_workarea', 'Can add IP to ingest workarea'),
            ('add_to_ingest_workarea_as_tar', 'Can add IP as tar to ingest workarea'),
            ('add_to_ingest_workarea_as_new', 'Can add IP as new generation to ingest workarea'),
            ('diff-check', 'Can diff-check IP'),
            ('query', 'Can query IP'),
            ('prepare_ip', 'Can prepare IP'),
            ('delete_first_generation', 'Can delete first generation of IP'),
            ('delete_last_generation', 'Can delete last generation of IP'),
            ('delete_archived', 'Can delete archived IP'),
            ('see_all_in_workspaces', 'Can see all IPs workspaces'),
        )

    def __str__(self):
        return self.object_identifier_value

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


class InformationPackageUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(InformationPackage, on_delete=models.CASCADE)


class InformationPackageGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(InformationPackage, on_delete=models.CASCADE)


class EventIP(models.Model):
    """
    Events related to IP
    """

    SUCCESS = 0
    FAILURE = 1

    OUTCOME_CHOICES = (
        (0, 'Success'),
        (1, 'Failure'),
    )

    id = models.BigAutoField(primary_key=True)
    eventIdentifierValue = models.UUIDField(default=uuid.uuid4, editable=False)
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
    linkingAgentIdentifierValue = models.CharField(max_length=255, blank=True)
    linkingAgentRole = models.CharField(max_length=255, blank=True)
    linkingObjectIdentifierValue = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["eventDateTime", "id"]
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
        (INGEST, 'ingest'),
        (ACCESS, 'access'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    ip = models.ForeignKey('ip.InformationPackage', on_delete=models.CASCADE, related_name='workareas')
    read_only = models.BooleanField(default=True)
    type = models.IntegerField(choices=TYPE_CHOICES, default=0)
    successfully_validated = jsonfield.JSONField(default=None, null=True)

    @property
    def path(self):
        area_dir = Path.objects.cached('entity', self.get_type_display() + '_workarea', 'value')
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
