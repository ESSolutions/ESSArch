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

import errno
import logging
import math
import os
import shutil
import tarfile
import uuid
import zipfile
from copy import deepcopy
from datetime import datetime
from os import walk
from time import sleep
from urllib.parse import urljoin

import requests
from celery import states as celery_states
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import connection, models, transaction
from django.db.models import (
    CharField,
    Count,
    Exists,
    F,
    Max,
    Min,
    OuterRef,
    Q,
    Sum,
)
from django.db.models.expressions import RawSQL
from django.db.models.functions import Cast
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from groups_manager.utils import get_permission_name
from guardian.shortcuts import assign_perm
from lxml import etree
from requests import RequestException
from rest_framework import exceptions
from rest_framework.response import Response
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from ESSArch_Core.auth.models import GroupGenericObjects, Member
from ESSArch_Core.configuration.models import Path, StoragePolicy
from ESSArch_Core.crypto import encrypt_remote_credentials
from ESSArch_Core.essxml.Generator.xmlGenerator import parseContent
from ESSArch_Core.fields import JSONField
from ESSArch_Core.fixity.format import FormatIdentifier
from ESSArch_Core.managers import OrganizationManager
from ESSArch_Core.profiles.models import (
    ProfileIP,
    ProfileIPData,
    ProfileSA,
    SubmissionAgreement as SA,
)
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.search.importers import get_backend as get_importer
from ESSArch_Core.search.ingest import index_path
from ESSArch_Core.storage.exceptions import StorageMediumFull
from ESSArch_Core.storage.models import (
    STORAGE_TARGET_STATUS_ENABLED,
    STORAGE_TARGET_STATUS_MIGRATE,
    STORAGE_TARGET_STATUS_READ_ONLY,
    StorageMedium,
    StorageMethod,
    StorageObject,
    StorageTarget,
)
from ESSArch_Core.util import (
    find_destination,
    generate_file_response,
    get_files_and_dirs,
    get_tree_size_and_count,
    in_directory,
    normalize_path,
    open_file,
    timestamp_to_datetime,
)
from ESSArch_Core.WorkflowEngine.util import create_workflow

logger = logging.getLogger('essarch.ip')

IP_LOCK_PREFIX = 'lock_ip_'
MESSAGE_DIGEST_ALGORITHM_CHOICES = (
    (StoragePolicy.MD5, 'MD5'),
    (StoragePolicy.SHA1, 'SHA-1'),
    (StoragePolicy.SHA224, 'SHA-224'),
    (StoragePolicy.SHA256, 'SHA-256'),
    (StoragePolicy.SHA384, 'SHA-384'),
    (StoragePolicy.SHA512, 'SHA-512'),
)
MESSAGE_DIGEST_ALGORITHM_CHOICES_DICT = {v: k for k, v in MESSAGE_DIGEST_ALGORITHM_CHOICES}


class AgentQuerySet(models.QuerySet):
    def with_notes(self, notes):
        qs = self.annotate(Count('notes', distinct=True)).filter(notes__count=len(notes))
        for n in notes:
            qs = qs.filter(notes__note=n)

        return qs


class AgentManager(models.Manager):
    def get_queryset(self):
        return AgentQuerySet(self.model, using=self._db)

    def from_mets_element(self, el):
        other_role = el.get("ROLE") == 'OTHER'
        other_type = el.get("TYPE") == 'OTHER'
        agent_role = el.get("OTHERROLE") if other_role else el.get("ROLE")
        agent_type = el.get("OTHERTYPE") if other_type else el.get("TYPE")
        name = el.xpath('*[local-name()="name"]')[0].text
        notes = [n.text for n in el.xpath('*[local-name()="note"]')]

        existing_agents_with_notes = self.model.objects.all().with_notes(notes)
        agent, created = self.model.objects.get_or_create(
            role=agent_role,
            type=agent_type,
            name=name,
            pk__in=existing_agents_with_notes,
            defaults={'other_role': other_role, 'other_type': other_type},
        )
        if created:
            AgentNote.objects.bulk_create(AgentNote(agent=agent, note=n) for n in notes)
        return agent


class Agent(models.Model):
    role = models.CharField(max_length=255)
    other_role = models.BooleanField(default=False)
    type = models.CharField(max_length=255)
    other_type = models.BooleanField(default=False)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=16)

    objects = AgentManager()

    def __str__(self):
        return self.name


class AgentNote(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='notes')
    note = models.CharField(max_length=255)


class InformationPackageQuerySet(models.QuerySet):
    def migratable(self):
        # TODO: This is really, really ugly but is required until Django 3.0 is released
        #
        # See:
        #  * https://github.com/django/django/pull/8119
        #  * https://github.com/django/django/pull/11062
        #  * https://github.com/django/django/pull/11677
        #  * https://code.djangoproject.com/ticket/30739

        # TODO: Exclude those that already has a task that has not succeeded (?)

        def mssql_wrapper(sql):
            if connection.vendor == 'microsoft':
                return '(CASE WHEN ({}) THEN 1 ELSE 0 END)'.format(sql)
            return sql

        method_with_old_migrate_and_new_enabled = StorageMethod.objects.annotate(
            status_migrate_with_ip=RawSQL(mssql_wrapper("""
                EXISTS(
                    SELECT 1 FROM storage_storagemethodtargetrelation U1
                    INNER JOIN storage_storagetarget U3 ON (U1.storage_target_id = U3.id)
                    INNER JOIN storage_storagemedium U4 ON (U3.id = U4.storage_target_id)
                    INNER JOIN storage_storageobject U5 ON (U4.id = U5.storage_medium_id)
                    WHERE (
                        U1.status=%s AND
                        U1.storage_method_id = (U0.id) AND
                        U5.ip_id=ip_informationpackage.id
                    )
                )"""), (STORAGE_TARGET_STATUS_MIGRATE,)
            ),
            status_enabled_with_ip=RawSQL(mssql_wrapper("""
                EXISTS(
                    SELECT 1 FROM storage_storagemethodtargetrelation U1
                    INNER JOIN storage_storagetarget U3 ON (U1.storage_target_id = U3.id)
                    INNER JOIN storage_storagemedium U4 ON (U3.id = U4.storage_target_id)
                    INNER JOIN storage_storageobject U5 ON (U4.id = U5.storage_medium_id)
                    WHERE (
                        U1.status=%s AND
                        U1.storage_method_id = (U0.id) AND
                        U5.ip_id=ip_informationpackage.id
                    )
                )"""), (STORAGE_TARGET_STATUS_ENABLED,)
            ),
            status_enabled_without_ip=RawSQL(mssql_wrapper("""
                EXISTS(
                    SELECT 1 FROM storage_storagemethodtargetrelation U1
                    WHERE (
                        U1.status=%s AND
                        U1.storage_method_id = (U0.id)
                    )
                )"""), (STORAGE_TARGET_STATUS_ENABLED,)
            ),
        ).filter(
            enabled=True,
            status_migrate_with_ip=True,
            status_enabled_without_ip=True,
            status_enabled_with_ip=False,
            storage_policies=OuterRef('policy'),
        )

        method_with_enabled_target_without_ip = StorageMethod.objects.annotate(
            enabled_target_without_ip=RawSQL(mssql_wrapper("""
                EXISTS(
                    SELECT 1 FROM storage_storagemethodtargetrelation AS U2
                    WHERE (
                        U2.status=%s AND U2.storage_method_id = (U0.id) AND NOT (EXISTS(
                            SELECT 1 FROM storage_storageobject U3
                            INNER JOIN storage_storagemedium U4 ON (U4.id = U3.storage_medium_id)
                            INNER JOIN storage_storagetarget U5 ON (U5.id = U4.storage_target_id)
                            WHERE U3.ip_id = ip_informationpackage.id
                            AND U5.id = U2.storage_target_id
                       ))
                   )
                )"""), (STORAGE_TARGET_STATUS_ENABLED,)
            ),
        ).filter(
            enabled=True,
            enabled_target_without_ip=True,
            storage_policies=OuterRef('policy')
        )

        return self.annotate(
            method_with_old_migrate_and_new_enabled_exists=Exists(method_with_old_migrate_and_new_enabled),
            method_with_enabled_target_without_ip_exists=Exists(method_with_enabled_target_without_ip),
        ).filter(
            Q(
                Q(method_with_enabled_target_without_ip_exists=True) |
                Q(method_with_old_migrate_and_new_enabled_exists=True)
            ),
            archived=True
        ).exclude(storage=None)


class InformationPackageManager(OrganizationManager):
    def get_queryset(self):
        return InformationPackageQuerySet(self.model, using=self._db)

    def visible_to_user(self, user):
        return self.for_user(user, 'view_informationpackage')

    def migratable(self):
        return self.get_queryset().migratable()


class InformationPackage(models.Model):
    """
    Information Package
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
    create_date = models.DateTimeField(_('create date'), auto_now_add=True)
    state = models.CharField(_('state'), max_length=255)

    object_path = models.CharField(max_length=255, blank=True)
    object_size = models.BigIntegerField(_('object size'), default=0)
    object_num_items = models.IntegerField(default=0)

    start_date = models.DateTimeField(_('start date'), null=True)
    end_date = models.DateTimeField(_('end date'), null=True)

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

    entry_date = models.DateTimeField(_('entry date'), null=True)
    entry_agent_identifier_value = models.CharField(max_length=255, blank=True)

    package_type = models.IntegerField(_('package type'), null=True, choices=PACKAGE_TYPE_CHOICES, default=SIP)
    preservation_level_value = models.IntegerField(choices=PRESERVATION_LEVEL_VALUE_CHOICES, default=1)

    delivery_type = models.CharField(max_length=255, blank=True)
    information_class = models.IntegerField(null=True, choices=INFORMATION_CLASS_CHOICES)
    generation = models.IntegerField(null=True)

    cached = models.BooleanField(_('cached'), default=False)
    archived = models.BooleanField(_('archived'), default=False)

    last_changed_local = models.DateTimeField(null=True)
    last_changed_external = models.DateTimeField(null=True)

    responsible = models.ForeignKey(
        'auth.User', verbose_name=_('responsible'), on_delete=models.SET_NULL,
        related_name='information_packages', null=True
    )

    policy = models.ForeignKey(
        'configuration.StoragePolicy',
        on_delete=models.PROTECT,
        related_name='information_packages',
        null=True,
    )
    aic = models.ForeignKey('self', on_delete=models.PROTECT, related_name='information_packages', null=True)

    sip_objid = models.CharField(max_length=255)
    sip_path = models.CharField(max_length=255)

    tag = models.ForeignKey(
        'tags.TagStructure',
        on_delete=models.SET_NULL,
        related_name='information_packages',
        null=True,
    )

    submission_agreement = models.ForeignKey(
        SA,
        on_delete=models.PROTECT,
        related_name='information_packages',
        default=None,
        null=True,
    )
    submission_agreement_data = models.ForeignKey(
        'profiles.SubmissionAgreementIPData',
        on_delete=models.SET_NULL,
        null=True,
    )
    submission_agreement_locked = models.BooleanField(default=False)
    agents = models.ManyToManyField(Agent, related_name='information_packages')

    objects = InformationPackageManager()

    def save(self, *args, **kwargs):
        if not self.object_identifier_value:
            self.object_identifier_value = str(self.pk)

        super().save(*args, **kwargs)

    def get_agent(self, role, type):
        try:
            return self.agents.get(role=role, type=type)
        except Agent.DoesNotExist:
            return None

    @classmethod
    def clear_locks(cls):
        return cache.delete_pattern(IP_LOCK_PREFIX + '*')

    def get_lock_key(self):
        return '{}{}'.format(IP_LOCK_PREFIX, str(self.pk))

    def is_locked(self):
        return self.get_lock_key() in cache

    def get_permissions(self, user, checker=None):
        return user.get_all_permissions(self)

    def get_migratable_storage_methods(self):
        # Gets storage methods that the IP will be migrated to

        if not self.archived or not self.storage.exists():
            return StorageMethod.objects.none()

        return self.policy.storage_methods.annotate(has_object=Exists(
            StorageObject.objects.filter(
                ip=self, storage_medium__storage_target__methods=OuterRef('pk'),
                storage_medium__storage_target__storage_method_target_relations__status=STORAGE_TARGET_STATUS_ENABLED,
            ))
        ).filter(enabled=True).exclude(has_object=True)

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

    @transaction.atomic
    def change_organization(self, organization):
        from ESSArch_Core.tags.models import TagVersion

        if organization.group_type.codename != 'organization':
            raise ValueError('{} is not an organization'.format(organization))
        ctype = ContentType.objects.get_for_model(self)
        GroupGenericObjects.objects.update_or_create(object_id=self.pk, content_type=ctype,
                                                     defaults={'group': organization})

        ctype = ContentType.objects.get_for_model(TagVersion)
        tag_versions = TagVersion.objects.annotate(id_as_char=Cast('pk', CharField())).filter(
            tag__information_package=self
        ).values('id_as_char')
        GroupGenericObjects.objects.filter(content_type=ctype, object_id__in=tag_versions).update(
            group=organization
        )

    @staticmethod
    def get_dirs(structure, data, root=""):
        for content in structure:
            if content.get('type') == 'folder':
                name = content.get('name')
                dirname = os.path.join(root, name)
                dirname = parseContent(dirname, data)
                if not content.get('create', True):
                    continue

                yield dirname
                for x in InformationPackage.get_dirs(content.get('children', []), data, dirname):
                    yield x

    def create_physical_model(self, structure, root=""):
        data = fill_specification_data(ip=self, sa=self.submission_agreement)
        structure = structure or self.get_structure()
        root = self.object_path if not root else root
        created = []

        try:
            for dirname in InformationPackage.get_dirs(structure, data, root):
                os.makedirs(dirname, exist_ok=True)
                created.append(dirname)
        except Exception:
            for dirname in created:
                try:
                    shutil.rmtree(dirname)
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise
            raise

    def create_new_generation(self, state, responsible, object_identifier_value):
        perms = deepcopy(getattr(settings, 'IP_CREATION_PERMS_MAP', {}))

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
            max_generation = InformationPackage.objects.select_for_update().filter(aic=self.aic).aggregate(
                Max('generation')
            )['generation__max']
            new_aip.generation = max_generation + 1
            new_aip.save()

        new_aip.object_identifier_value = object_identifier_value or str(new_aip.pk)
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
        organization.add_object(new_aip)

        for perm in user_perms:
            perm_name = get_permission_name(perm, new_aip)
            assign_perm(perm_name, member.django_user, new_aip)

        return new_aip

    def get_content_type_importer_name(self):
        ct_profile = self.get_profile('content_type')
        if ct_profile is None:
            msg = 'No content_type profile set for {objid}'.format(objid=self.object_identifier_value)
            logger.info(msg)
            return None

        try:
            return ct_profile.specification['name']
        except KeyError:
            msg = 'No content type importer specified in {profile}'.format(profile=ct_profile.name)
            logger.exception(msg)
            raise exceptions.APIException(msg)

    def get_content_type_file(self):
        try:
            ctsdir, ctsfile = find_destination('content_type_specification', self.get_structure(), self.object_path)
        except ProfileIP.DoesNotExist:
            return None

        if ctsdir is None:
            return None

        full_path = os.path.join(ctsdir, ctsfile)
        return parseContent(full_path, fill_specification_data(ip=self, ignore=['_CTS_PATH', '_CTS_SCHEMA_PATH']))

    def get_content_type_schema_file(self):
        try:
            ctsdir, ctsfile = find_destination(
                'content_type_specification_schema',
                self.get_structure(), self.object_path,
            )
        except ProfileIP.DoesNotExist:
            return None
        if ctsdir is None:
            return None

        full_path = os.path.join(ctsdir, ctsfile)
        return parseContent(full_path, fill_specification_data(ip=self, ignore=['_CTS_PATH', '_CTS_SCHEMA_PATH']))

    def get_archive_tag(self):
        if self.tag is not None:
            return self.tag

        ct_importer_name = self.get_content_type_importer_name()
        if ct_importer_name is None:
            return None
        ct_importer = get_importer(ct_importer_name)()
        ct_file = self.get_content_type_file()
        if ct_file is None:
            return None

        ct_file = os.path.relpath(ct_file, self.object_path)
        cts_file = self.open_file(ct_file)
        tag = ct_importer.get_archive(cts_file)

        if tag is None:
            return self.tag

        return tag

    def check_db_sync(self):
        if self.last_changed_local is not None and self.last_changed_external is not None:
            return (self.last_changed_local - self.last_changed_external).total_seconds() == 0

    def new_version_in_progress(self):
        ip = self.related_ips(cached=False).filter(workareas__read_only=False).first()

        if ip is not None:
            return ip.workareas.first()

        return None

    def create_profile_rels(self, profile_types, user):
        sa = self.submission_agreement
        extra_data = fill_specification_data(ip=self, sa=sa)
        for p_type in profile_types:
            if ProfileIP.objects.filter(ip=self, profile__profile_type=p_type).exists():
                continue
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

            for field in sa.template:
                if field['key'] not in data:
                    try:
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
        try:
            return ProfileIP.objects.get(ip=self, profile__profile_type=profile_type).profile
        except ProfileIP.DoesNotExist:
            return None

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
        except BaseException:
            return 'tar'

    def get_checksum_algorithm(self):
        if self.package_type != InformationPackage.AIP:
            name = self.get_profile_data('transfer_project').get(
                'checksum_algorithm', 'SHA-256'
            )
        else:
            name = self.policy.get_checksum_algorithm_display().upper()

        return name

    def get_email_recipient(self):
        try:
            return self.get_profile_data('transfer_project').get(
                'preservation_organization_receiver_email'
            )
        except BaseException:
            return None

    def get_allow_unknown_file_types(self):
        profile_type = self.get_package_type_display().lower()
        return self.get_profile_data(profile_type).get('allow_unknown_file_types', False)

    def get_allow_encrypted_files(self):
        profile_type = self.get_package_type_display().lower()
        return self.get_profile_data(profile_type).get('allow_encrypted_files', False)

    def get_structure(self):
        if self.package_type == InformationPackage.AIP and self.state == 'Prepared':
            ip_profile_type = 'sip'
        else:
            ip_profile_type = self.get_package_type_display().lower()

        ip_profile_rel = self.get_profile_rel(ip_profile_type)
        return ip_profile_rel.profile.structure

    def get_content_mets_file_path(self):
        mets_dir, mets_name = find_destination("mets_file", self.get_structure())
        if mets_dir is not None:
            path = os.path.join(mets_dir, mets_name)
            path = parseContent(path, fill_specification_data(ip=self))
        else:
            path = 'mets.xml'

        return normalize_path(os.path.join(self.object_path, path))

    def get_premis_file_path(self):
        try:
            premis_dir, premis_name = find_destination("preservation_description_file", self.get_structure())
        except ProfileIP.DoesNotExist:
            return None

        if premis_dir is not None:
            path = os.path.join(premis_dir, premis_name)
        else:
            path = 'metadata/premis.xml'

        return normalize_path(os.path.join(self.object_path, path))

    def get_events_file_path(self, from_container=False):
        if not from_container and os.path.isfile(self.object_path):
            return os.path.splitext(self.object_path)[0] + '_ipevents.xml'

        ip_profile = self.get_profile(self.get_package_type_display().lower())
        structure = ip_profile.structure

        events_dir, events_file = find_destination('events_file', structure)
        if events_dir is not None:
            full_path = os.path.join(events_dir, events_file)
            return normalize_path(parseContent(full_path, fill_specification_data(ip=self)))

        return 'ipevents.xml'

    def related_ips(self, cached=True):
        if self.package_type == InformationPackage.AIC:
            if not cached:
                return InformationPackage.objects.filter(aic=self)

            return self.information_packages.all()

        if self.aic is not None:
            if not cached:
                return InformationPackage.objects.filter(aic=self.aic).exclude(pk=self.pk)

            if 'information_packages' in getattr(self.aic, '_prefetched_objects_cache', {}):
                # prefetched, don't need to filter
                return self.aic.information_packages
            else:
                return self.aic.information_packages.exclude(pk=self.pk)

        return InformationPackage.objects.none()

    @property
    def step_state(self):
        """
        Gets the state of the IP based on its tasks

        Args:

        Returns:
            Can be one of the following:
            SUCCESS, STARTED, FAILURE, PENDING

            Which is decided by five scenarios:

            * If there are tasks and they are all pending,
              then PENDING.
            * If a task has started, then STARTED.
            * If a task has failed, then FAILURE.
            * If all tasks have succeeded, then SUCCESS.

            If the IP is an AIC, then the same algorithm is
            applied on the related IPs instead
        """

        if self.package_type == InformationPackage.AIC:
            ips = self.related_ips()
            state = celery_states.SUCCESS

            for ip in ips:
                ip_step_state = ip.step_state

                if ip_step_state == celery_states.STARTED or ip_step_state == celery_states.REVOKED:
                    state = ip_step_state
                if (ip_step_state == celery_states.PENDING and
                        state not in [celery_states.STARTED, celery_states.REVOKED]):
                    state = ip_step_state
                if ip_step_state == celery_states.FAILURE:
                    return ip_step_state

            return state

        tasks = self.processtask_set.filter(Q(hidden=False) | Q(hidden__isnull=True))
        state = celery_states.SUCCESS
        for task in tasks:
            task_status = task.status

            if task_status == celery_states.STARTED or task_status == celery_states.REVOKED:
                state = task_status
            if (task_status == celery_states.PENDING and
                    state not in [celery_states.STARTED, celery_states.REVOKED]):
                state = task_status
            if task_status == celery_states.FAILURE:
                return task_status

        return state

    def status(self):
        if self.state == "Prepared":
            return 100
        elif self.state == "Preparing":
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

                progress += math.ceil(ip_profiles_locked.count() * ((100 - progress) / sa_profiles.count()))

            except ZeroDivisionError:
                pass

            return progress

        step_progress = None
        task_progress = None

        steps = self.steps.filter(Q(parent_step__isnull=True) | Q(parent_step__information_package__isnull=True))
        if steps.exists():
            step_progress = sum([s.progress for s in steps])

        tasks = self.processtask_set.filter(
            Q(
                Q(processstep__isnull=True) |
                Q(processstep__information_package__isnull=True)
            ),
            steps_on_errors=None,
            processtask=None,
        )
        if tasks.exists():
            task_progress = tasks.aggregate(Sum('progress'))['progress__sum']

        if tasks.exists() or steps.exists():
            progress = task_progress or 0
            progress += step_progress or 0

            return progress / (steps.count() + tasks.count())

        return 100

    def list_files(self, path=''):
        fullpath = os.path.join(self.object_path, path).rstrip('/')
        if os.path.basename(self.object_path) == path and os.path.isfile(self.object_path):
            if tarfile.is_tarfile(self.object_path):
                with tarfile.open(self.object_path) as tar:
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
                    return entries

            elif zipfile.is_zipfile(self.object_path) and os.path.splitext(self.object_path)[1] == '.zip':
                with zipfile.ZipFile(self.object_path) as zipf:
                    entries = []
                    for member in zipf.filelist:
                        if member.filename.endswith('/'):
                            continue

                        entries.append({
                            "name": member.filename,
                            "type": 'file',
                            "size": member.file_size,
                            "modified": datetime(*member.date_time),
                        })
                    return entries

        if os.path.isfile(self.object_path) and not path:
            container = self.object_path
            xml = os.path.splitext(container)[0] + '.xml'
            entries = [{
                "name": os.path.basename(container),
                "type": 'file',
                "size": os.path.getsize(container),
                "modified": timestamp_to_datetime(os.path.getmtime(container)),
            }]

            if os.path.isfile(xml):
                entries.append({
                    "name": os.path.basename(xml),
                    "type": 'file',
                    "size": os.path.getsize(xml),
                    "modified": timestamp_to_datetime(os.path.getmtime(xml)),
                })

            return entries

        entries = []
        for entry in sorted(get_files_and_dirs(fullpath), key=lambda x: x.name):
            try:
                entry_type = "dir" if entry.is_dir() else "file"
                size, _ = get_tree_size_and_count(entry.path)

                entries.append(
                    {
                        "name": os.path.basename(entry.path),
                        "type": entry_type,
                        "size": size,
                        "modified": timestamp_to_datetime(entry.stat().st_mtime),
                    }
                )
            except OSError as e:
                # the file might be deleted (e.g. temporary upload files) while we get additional data,
                # if they are we ignore them. If there is another error, we raise it

                if e.errno != errno.ENOENT:
                    raise

        return entries

    def get_path(self):
        return self.object_path

    def validate_path(self, path):
        fullpath = os.path.join(self.object_path, path)
        if not in_directory(fullpath, self.object_path) and fullpath != os.path.splitext(self.object_path)[0] + '.xml':
            raise exceptions.ValidationError('Illegal path: {s}'.format(path))

    def get_path_response(self, path, request, force_download=False, paginator=None):
        self.validate_path(path)
        try:
            if not path:
                raise OSError(errno.EISDIR, os.strerror(errno.EISDIR), path)

            if os.path.isfile(self.object_path):
                container_path = os.path.join(os.path.dirname(self.object_path), path.split('/', 1)[0])
                container_path = normalize_path(container_path)
                if container_path == self.object_path:
                    path = path.split('/', 1)[1]

            fid = FormatIdentifier(allow_unknown_file_types=True)
            content_type = fid.get_mimetype(path)
            return generate_file_response(
                self.open_file(path, 'rb'),
                content_type,
                force_download=force_download,
                name=path
            )
        except OSError as e:
            if e.errno == errno.ENOENT:
                raise exceptions.NotFound

            # Windows raises PermissionDenied (errno.EACCES) when trying to use
            # open() on a directory
            if os.name == 'nt':
                if e.errno not in (errno.EACCES, errno.EISDIR):
                    raise
            elif e.errno != errno.EISDIR:
                raise
        except IndexError:
            if force_download:
                fid = FormatIdentifier(allow_unknown_file_types=True)
                content_type = fid.get_mimetype(path)
                return generate_file_response(
                    self.open_file(self.object_path, 'rb'),
                    content_type,
                    force_download=force_download,
                    name=path
                )

        entries = self.list_files(path)
        if paginator is not None:
            paginated = paginator.paginate_queryset(entries, request)
            return paginator.get_paginated_response(paginated)
        return Response(entries)

    def create_preservation_workflow(self):
        generate_premis = self.profile_locked('preservation_metadata')

        try:
            workarea_id = self.workareas.get(read_only=False).pk
        except Workarea.DoesNotExist:
            workarea_id = None

        cache_storage = self.policy.cache_storage
        container_methods = self.policy.storage_methods.secure_storage().filter(
            remote=False, enabled=True,
        ).exclude(pk=cache_storage.pk)
        non_container_methods = self.policy.storage_methods.archival_storage().filter(
            remote=False, enabled=True,
        ).exclude(pk=cache_storage.pk)
        remote_methods = self.policy.storage_methods.filter(
            remote=True, enabled=True,
        ).exclude(pk=cache_storage.pk)

        remote_servers = set([
            method.enabled_target.remote_server
            for method in remote_methods
        ])

        profile_type = self.get_package_type_display().lower()
        write_to_search_index = self.get_profile_data(profile_type).get('index_files', True)

        remote_temp_container_transfer = {
            "step": True,
            "parallel": True,
            "name": "Write temporary files to remote hosts",
            "children": [
                {
                    "step": True,
                    "parallel": True,
                    "name": "Write temporary files to remote host",
                    "children": [
                        {
                            "name": "ESSArch_Core.tasks.CopyFile",
                            "label": "Transfer temporary container to {}".format(remote_server.split(',')[0]),
                            "args": [
                                "{{TEMP_CONTAINER_PATH}}",
                                urljoin(
                                    remote_server.split(',')[0],
                                    reverse('informationpackage-add-file-from-master')
                                ),
                                encrypt_remote_credentials(remote_server),
                            ],
                        },
                        {
                            "name": "ESSArch_Core.tasks.CopyFile",
                            "label": "Transfer temporary AIP xml to {}".format(remote_server.split(',')[0]),
                            "args": [
                                "{{TEMP_METS_PATH}}",
                                urljoin(
                                    remote_server.split(',')[0],
                                    reverse('informationpackage-add-file-from-master')
                                ),
                                encrypt_remote_credentials(remote_server),
                            ],
                        },
                        {
                            "name": "ESSArch_Core.tasks.CopyFile",
                            "run_if": "{{TEMP_AIC_METS_PATH}}",
                            "label": "Transfer temporary AIC xml to {}".format(remote_server.split(',')[0]),
                            "args": [
                                "{{TEMP_AIC_METS_PATH}}",
                                urljoin(
                                    remote_server.split(',')[0],
                                    reverse('informationpackage-add-file-from-master')
                                ),
                                encrypt_remote_credentials(remote_server),
                            ],
                        },
                    ]
                } for remote_server in remote_servers
            ]
        }

        remote_temp_container_to_storage_method = {
            "step": True,
            "parallel": True,
            "name": "Write temporary container to storage_methods",
            "children": [
                {
                    "step": True,
                    "name": "Write container to {}".format(method.pk),
                    "children": [
                        {
                            "name": "ESSArch_Core.ip.tasks.PreserveInformationPackage",
                            "label": "Write to storage method",
                            "args": [str(method.pk)],
                        }
                    ]
                } for method in remote_methods
            ]
        }

        remote_containers_step = {
            "step": True,
            "name": "Write remote containers",
            "children": [
                remote_temp_container_transfer,
                remote_temp_container_to_storage_method,
            ],
        }

        workflow = [
            {
                "name": "ESSArch_Core.ip.tasks.GeneratePremis",
                "label": "Generate premis",
                "if": workarea_id and generate_premis,
            },
            {
                "name": "ESSArch_Core.ip.tasks.GenerateContentMets",
                "label": "Generate content-mets",
                "if": workarea_id,
            },
            {
                "step": True,
                "name": "Write to storage",
                "children": [
                    {
                        "step": True,
                        "name": "Write to cache",
                        "children": [
                            {
                                "name": "ESSArch_Core.ip.tasks.PreserveInformationPackage",
                                "label": "Write to storage medium",
                                "args": [str(cache_storage.pk)],
                            },
                            {
                                "name": "ESSArch_Core.ip.tasks.WriteInformationPackageToSearchIndex",
                                "label": "Write to search index",
                                "if": write_to_search_index,
                            },
                            {
                                "name": "ESSArch_Core.ip.tasks.CreateReceipt",
                                "label": "Create receipt",
                                "args": [
                                    None,
                                    "xml",
                                    "receipts/xml.json",
                                    "{{PATH_RECEIPTS}}/xml/{{_OBJID}}_{% now 'ymdHis' %}.xml",
                                    "success",
                                    "Cached and indexed {{OBJID}}",
                                    "Cached and indexed {{OBJID}}",
                                ],
                            }
                        ]
                    },
                    {
                        "step": True,
                        "name": "Write to storage methods",
                        "parallel": True,
                        "children": [
                            {
                                "step": True,
                                "parallel": True,
                                "name": "Write non-containers to storage methods",
                                "if": non_container_methods.exists(),
                                "children": [
                                    {
                                        "name": "ESSArch_Core.ip.tasks.PreserveInformationPackage",
                                        "label": "Write to storage method",
                                        "args": [str(method.pk)],
                                    } for method in non_container_methods
                                ]
                            },
                            {
                                "step": True,
                                "name": "Write containers",
                                "if": container_methods.exists() or remote_methods.exists(),
                                "children": [
                                    {
                                        "name": "ESSArch_Core.ip.tasks.CreateContainer",
                                        "label": "Create temporary container",
                                        "args": ["{{OBJPATH}}", "{{TEMP_CONTAINER_PATH}}"],
                                    },
                                    {
                                        "name": "ESSArch_Core.ip.tasks.GeneratePackageMets",
                                        "label": "Create container mets",
                                        "args": [
                                            "{{TEMP_CONTAINER_PATH}}",
                                            "{{TEMP_METS_PATH}}",
                                        ]
                                    },
                                    {
                                        "name": "ESSArch_Core.ip.tasks.GenerateAICMets",
                                        "label": "Create container aic mets",
                                        "args": ["{{TEMP_AIC_METS_PATH}}"]
                                    },

                                    {
                                        "step": True,
                                        "parallel": True,
                                        "name": "Write containers to storage methods",
                                        "children": [
                                            {
                                                "step": True,
                                                "parallel": True,
                                                "name": "Write local containers",
                                                "children": [
                                                    {
                                                        "name": "ESSArch_Core.ip.tasks.PreserveInformationPackage",
                                                        "label": "Write to storage method",
                                                        "args": [str(method.pk)],
                                                    } for method in container_methods
                                                ],
                                            },
                                            remote_containers_step,
                                        ],
                                    },
                                    {
                                        "name": "ESSArch_Core.tasks.DeleteFiles",
                                        "label": "Delete temporary container",
                                        "args": ["{{TEMP_CONTAINER_PATH}}"]
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
            {
                "name": "ESSArch_Core.ip.tasks.MarkArchived",
                "label": "Mark as archived",
            },
            {
                "name": "ESSArch_Core.ip.tasks.DeleteWorkarea",
                "label": "Delete from workarea",
                "if": workarea_id,
                "args": [str(workarea_id)],
            },
        ]

        return workflow

    def create_access_workflow(self, user, tar=False, extracted=False, new=False, object_identifier_value=None):
        if not self.archived:
            ingest_workarea = Path.objects.get(entity='ingest_workarea').value
            container = os.path.isfile(self.object_path)
            ingest_workarea_user = os.path.join(ingest_workarea, user.username, self.object_identifier_value)

            workflow = [
                {
                    "name": "ESSArch_Core.ip.tasks.CreateWorkarea",
                    "label": "Create workarea",
                    "args": [str(self.pk), str(user.pk), Workarea.INGEST, True]
                },
                {
                    "name": "ESSArch_Core.tasks.ExtractTAR",
                    "label": "Extract container to workarea",
                    "if": container and extracted,
                    "args": [
                        self.object_path,
                        ingest_workarea_user,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.CopyFile",
                    "label": "Copy information package to workarea",
                    "if": container and not extracted,
                    "args": [
                        self.object_path,
                        ingest_workarea_user,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.CopyDir",
                    "label": "Copy information package to workarea",
                    "if": not container,
                    "args": [
                        self.object_path,
                        ingest_workarea_user,
                    ],
                },
            ]
            workflow = {"step": True, "name": "Access IP", "children": workflow}
            return create_workflow([workflow], self, name='Access Information Package')

        if tar:
            try:
                storage_object = self.storage.readable().secure_storage().fastest()[0]
            except IndexError:
                NO_READABLE_LONG_TERM_STORAGE_ERROR_MSG = (
                    'No readable long-term storage object for {} found, getting fastest storage object'.format(
                        self.object_identifier_value
                    )
                )
                logger.debug(NO_READABLE_LONG_TERM_STORAGE_ERROR_MSG)
                storage_object = self.get_fastest_readable_storage_object()
        else:
            storage_object = self.get_fastest_readable_storage_object()

        is_cached_storage_object = storage_object.is_cache_for_ip(self)

        cache_storage = self.policy.cache_storage
        try:
            cache_target = cache_storage.enabled_target
            if not cache_target.storagemedium_set.writeable().exists():
                cache_target = None
            else:
                cache_target = cache_target.target
        except StorageTarget.DoesNotExist:
            cache_target = None

        temp_dir = Path.objects.get(entity='temp').value
        temp_object_path = self.get_temp_object_path()
        temp_container_path = self.get_temp_container_path()
        temp_mets_path = self.get_temp_container_xml_path()
        temp_aic_mets_path = self.get_temp_container_aic_xml_path() if self.aic else None

        storage_medium = storage_object.storage_medium
        storage_target = storage_medium.storage_target

        access_workarea = Path.objects.get(entity='access_workarea').value

        if new:
            dst_object_identifier_value = object_identifier_value or str(uuid.uuid4())
        else:
            dst_object_identifier_value = self.object_identifier_value

        access_workarea_user = os.path.join(access_workarea, user.username, dst_object_identifier_value)
        access_workarea_user_container = '{}.{}'.format(access_workarea_user, self.get_container_format().lower())
        access_workarea_user_package_xml = '{}.{}'.format(access_workarea_user, 'xml')
        access_workarea_user_aic_xml = os.path.join(
            access_workarea, user.username, self.aic.object_identifier_value
        ) + '.xml'

        if extracted or new:
            os.makedirs(access_workarea_user, exist_ok=True)

        if storage_target.remote_server:
            # AccessAIP instructs and waits for ip.access to transfer files from remote
            # to master. Then we use CopyFile to copy files from local temp to workspace

            workflow = [
                {
                    "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                    "label": "Access AIP",
                    "args": [str(self.pk)],
                    "params": {
                        "storage_object": storage_object.pk,
                        'dst': temp_dir
                    },
                },
                {
                    "name": "ESSArch_Core.tasks.ExtractTAR",
                    "label": "Extract temporary container to cache",
                    "if": cache_target is not None,
                    "allow_failure": True,
                    "args": [
                        temp_container_path,
                        cache_target,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.ExtractTAR",
                    "label": "Extract temporary container to workspace",
                    "if": extracted,
                    "args": [
                        temp_container_path,
                        access_workarea_user,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.CopyFile",
                    "label": "Copy temporary container to workspace",
                    "if": tar,
                    "args": [
                        temp_container_path,
                        access_workarea_user_container,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.CopyFile",
                    "label": "Copy temporary AIP xml to workspace",
                    "if": tar,
                    "args": [
                        temp_mets_path,
                        access_workarea_user,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.CopyFile",
                    "label": "Copy temporary AIC xml to workspace",
                    "if": tar,
                    "args": [
                        temp_aic_mets_path,
                        access_workarea_user,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.DeleteFiles",
                    "label": "Delete temporary container",
                    "args": [temp_container_path]
                },
                {
                    "name": "ESSArch_Core.tasks.DeleteFiles",
                    "label": "Delete temporary AIP xml",
                    "args": [temp_mets_path]
                },
                {
                    "name": "ESSArch_Core.tasks.DeleteFiles",
                    "label": "Delete temporary AIC xml",
                    "args": [temp_aic_mets_path]
                },
            ]
        else:
            if is_cached_storage_object:
                workflow = [
                    {
                        "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                        "label": "Access AIP",
                        "if": extracted,
                        "args": [str(self.pk)],
                        "params": {
                            "storage_object": storage_object.pk,
                            'dst': access_workarea_user
                        },
                    },
                    {
                        "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                        "label": "Access AIP",
                        "if": tar,
                        "args": [str(self.pk)],
                        "params": {
                            "storage_object": storage_object.pk,
                            'dst': temp_object_path,
                        },
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.CreateContainer",
                        "label": "Create temporary container",
                        "if": tar,
                        "args": [temp_object_path, access_workarea_user_container],
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.GeneratePackageMets",
                        "label": "Create container mets",
                        "if": tar,
                        "args": [
                            temp_object_path,
                            access_workarea_user_package_xml,
                        ]
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.GenerateAICMets",
                        "label": "Create container aic mets",
                        "if": tar,
                        "args": [access_workarea_user_aic_xml]
                    },
                ]

            elif storage_object.container:
                # reading from long-term storage

                workflow = [
                    {
                        "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                        "label": "Access AIP",
                        "args": [str(self.pk)],
                        "params": {
                            "storage_object": storage_object.pk,
                            'dst': temp_dir
                        },
                    },
                    {
                        "name": "ESSArch_Core.tasks.ExtractTAR",
                        "label": "Extract temporary container to cache",
                        "if": cache_target is not None,
                        "allow_failure": True,
                        "args": [
                            temp_container_path,
                            cache_target,
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.ExtractTAR",
                        "label": "Extract temporary container to workspace",
                        "if": extracted,
                        "args": [
                            temp_container_path,
                            access_workarea_user,
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.CopyFile",
                        "label": "Copy temporary container to workspace",
                        "if": tar,
                        "args": [
                            temp_container_path,
                            access_workarea_user_container,
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.CopyFile",
                        "label": "Copy temporary AIP xml to workspace",
                        "if": tar,
                        "args": [
                            temp_mets_path,
                            access_workarea_user_package_xml,
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.CopyFile",
                        "label": "Copy temporary AIC xml to workspace",
                        "if": tar,
                        "args": [
                            temp_aic_mets_path,
                            access_workarea_user_aic_xml,
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.DeleteFiles",
                        "label": "Delete temporary container",
                        "args": [temp_container_path]
                    },
                    {
                        "name": "ESSArch_Core.tasks.DeleteFiles",
                        "label": "Delete temporary AIP xml",
                        "args": [temp_mets_path]
                    },
                    {
                        "name": "ESSArch_Core.tasks.DeleteFiles",
                        "label": "Delete temporary AIC xml",
                        "args": [temp_aic_mets_path]
                    },
                ]
            else:
                # reading from non long-term storage

                workflow = [
                    {
                        "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                        "label": "Copy AIP to cache",
                        "if": cache_target is not None,
                        "allow_failure": True,
                        "args": [str(self.pk)],
                        "params": {
                            "storage_object": storage_object.pk,
                            "dst": os.path.join(cache_target, self.object_identifier_value),
                        },
                    },
                    {
                        "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                        "label": "Access AIP",
                        "if": extracted,
                        "args": [str(self.pk)],
                        "params": {
                            "storage_object": storage_object.pk,
                            'dst': access_workarea_user
                        },
                    },
                    {
                        "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                        "label": "Access AIP",
                        "if": tar,
                        "args": [str(self.pk)],
                        "params": {
                            "storage_object": storage_object.pk,
                            'dst': temp_object_path,
                        },
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.CreateContainer",
                        "label": "Create temporary container",
                        "if": tar,
                        "args": [temp_object_path, access_workarea_user_container],
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.GeneratePackageMets",
                        "label": "Create container mets",
                        "if": tar,
                        "args": [
                            temp_object_path,
                            access_workarea_user_package_xml,
                        ]
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.GenerateAICMets",
                        "label": "Create container aic mets",
                        "if": tar,
                        "args": [access_workarea_user_aic_xml]
                    },
                ]

        if new:
            new_aip = self.create_new_generation('Access Workarea', user, dst_object_identifier_value)
            new_aip.object_path = access_workarea_user
            new_aip.save()
        else:
            new_aip = self

        workflow.append({
            "name": "ESSArch_Core.ip.tasks.CreateWorkarea",
            "label": "Create workarea",
            "args": [str(new_aip.pk), str(user.pk), Workarea.ACCESS, not new]
        })
        workflow = {"step": True, "name": "Access AIP", "children": workflow}
        return create_workflow([workflow], self, name='Access Information Package')

    def write_to_search_index(self, task):
        srcdir = self.object_path
        ct_profile = self.get_profile('content_type')
        indexed_files = []

        if ct_profile is not None:
            cts = self.get_content_type_file()
            if os.path.isfile(cts):
                logger.info('Found content type specification: {path}'.format(path=cts))
                try:
                    ct_importer_name = ct_profile.specification['name']
                except KeyError:
                    logger.exception('No content type importer specified in profile')
                    raise
                ct_importer = get_importer(ct_importer_name)(task)
                indexed_files = ct_importer.import_content(cts, ip=self)
            else:
                err = "Content type specification not found"
                logger.error('{err}: {path}'.format(err=err, path=cts))
                raise OSError(errno.ENOENT, err, cts)

        for root, dirs, files in walk(srcdir):
            for d in dirs:
                src = os.path.join(root, d)
                index_path(self, src)

            for f in files:
                src = os.path.join(root, f)
                try:
                    # check if file has already been indexed
                    indexed_files.remove(src)
                except ValueError:
                    # file has not been indexed, index it
                    index_path(self, src)

    def get_cached_storage_object(self):
        cache_method = self.policy.cache_storage
        return self.storage.get(
            storage_medium__storage_target__storage_method_target_relations__status__in=[
                STORAGE_TARGET_STATUS_ENABLED,
                STORAGE_TARGET_STATUS_READ_ONLY,
            ],
            storage_medium__storage_target__methods=cache_method
        )

    def get_fastest_readable_storage_object(self):
        NO_READABLE_CACHED_STORAGE_ERROR_MSG = (
            'No readable cached storage object for {} found, getting fastest storage object'.format(
                self.object_identifier_value
            )
        )
        cached_storage = None

        try:
            logger.debug('Getting readable storage object from cache for {}'.format(self.object_identifier_value))
            cached_storage = self.get_cached_storage_object()
        except StorageObject.DoesNotExist:
            logger.debug(NO_READABLE_CACHED_STORAGE_ERROR_MSG)

        if cached_storage is None or not cached_storage.readable():
            logger.debug(NO_READABLE_CACHED_STORAGE_ERROR_MSG)
            try:
                return self.storage.readable().fastest()[0]
            except IndexError:
                raise StorageObject.DoesNotExist('No readable storage object available')

        return cached_storage

    def get_temp_object_path(self):
        temp_dir = Path.objects.get(entity='temp').value
        return os.path.join(temp_dir, self.object_identifier_value)

    def get_temp_container_path(self):
        temp_dir = Path.objects.get(entity='temp').value
        container_format = self.get_container_format()
        return os.path.join(temp_dir, self.object_identifier_value + '.{}'.format(container_format))

    def get_temp_container_xml_path(self):
        temp_dir = Path.objects.get(entity='temp').value
        return os.path.join(temp_dir, self.object_identifier_value + '.xml')

    def get_temp_container_aic_xml_path(self):
        temp_dir = Path.objects.get(entity='temp').value
        return os.path.join(temp_dir, self.aic.object_identifier_value + '.xml')

    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logger, logging.DEBUG))
    def update_remote_ip(self, host, session):
        from ESSArch_Core.ip.serializers import InformationPackageFromMasterSerializer

        remote_ip = urljoin(host, reverse('informationpackage-add-from-master'))
        data = InformationPackageFromMasterSerializer(instance=self).data
        response = session.post(remote_ip, json=data, timeout=10)
        response.raise_for_status()

    @retry(retry=retry_if_exception_type(StorageMediumFull), reraise=True, stop=stop_after_attempt(2),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logger, logging.DEBUG))
    def preserve(self, src: list, storage_target, container: bool, task):
        qs = StorageMedium.objects.filter(
            storage_target__methods__containers=container,
        ).writeable().order_by('last_changed_local')

        write_size = 0
        for s in src:
            write_size += get_tree_size_and_count(s)[0]

        if storage_target.remote_server:
            host, user, passw = storage_target.remote_server.split(',')
            session = requests.Session()
            session.verify = settings.REQUESTS_VERIFY
            session.auth = (user, passw)

            self.update_remote_ip(host, session)

            # if the remote server already has completed
            # then we only want to get the result from it,
            # not run it again. If it has failed then
            # we want to retry it

            r = task.get_remote_copy(session, host)
            if r.status_code == 404:
                # the task does not exist
                task.create_remote_copy(session, host)
                task.run_remote_copy(session, host)
            else:
                remote_data = r.json()
                task.status = remote_data['status']
                task.progress = remote_data['progress']
                task.result = remote_data['result']
                task.traceback = remote_data['traceback']
                task.exception = remote_data['exception']
                task.save()

                if task.status != celery_states.SUCCESS:
                    task.retry_remote_copy(session, host)

            while task.status not in celery_states.READY_STATES:
                r = task.get_remote_copy(session, host)

                remote_data = r.json()
                task.status = remote_data['status']
                task.progress = remote_data['progress']
                task.result = remote_data['result']
                task.traceback = remote_data['traceback']
                task.exception = remote_data['exception']
                task.save()

                sleep(5)

            if task.status in celery_states.EXCEPTION_STATES:
                task.reraise()

            storage_object = StorageObject.create_from_remote_copy(host, session, task.result)
        else:
            storage_medium, created = storage_target.get_or_create_storage_medium(qs=qs)

            new_size = storage_medium.used_capacity + write_size
            if new_size > storage_target.max_capacity > 0:
                storage_medium.mark_as_full()
                raise StorageMediumFull('No space left on storage medium "{}"'.format(str(storage_medium.pk)))

            storage_backend = storage_target.get_storage_backend()
            storage_medium.prepare_for_write()

            storage_object = storage_backend.write(src, self, container, storage_medium)
            StorageMedium.objects.filter(pk=storage_medium.pk).update(
                used_capacity=F('used_capacity') + write_size
            )

        return str(storage_object.pk)

    def access(self, storage_object, task, dst=None):
        logger.debug('Accessing information package {} from storage object {}'.format(
            self.object_identifier_value, str(storage_object.pk),
        ))

        storage_object.read(dst, task)

    def open_file(self, path='', *args, **kwargs):
        if self.archived:
            storage_obj = self.storage.readable().fastest().first()
            if storage_obj is None:
                raise ValueError("No readable storage configured for IP")
            return storage_obj.open(path, *args, **kwargs)
        if os.path.isfile(self.object_path) and path:
            if path == self.object_path:
                return open(path, *args, **kwargs)

            xmlfile = self.package_mets_path
            if not xmlfile:
                xmlfile = os.path.join(
                    os.path.dirname(self.object_path),
                    '{}.xml'.format(self.object_identifier_value)
                )
            if os.path.join(os.path.dirname(self.object_path), path) == xmlfile:
                return open(xmlfile, *args)

            return open_file(
                path, *args, container=self.object_path,
                container_prefix=self.object_identifier_value, **kwargs
            )

        return open(os.path.join(self.object_path, path), *args, **kwargs)

    def delete_files(self):
        path = self.get_path()

        if self.archived:
            for storage_obj in self.storage.all():
                storage_obj.delete_files()
                storage_obj.delete()

            return

        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            no_ext = os.path.splitext(path)[0]
            for fl in [no_ext + '.' + ext for ext in ['xml', 'tar', 'zip']]:
                try:
                    os.remove(fl)
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise

    def delete_workareas(self):
        for workarea in self.workareas.all():
            workarea.delete_files()
            workarea.delete()

    class Meta:
        ordering = ["generation", "-create_date"]
        verbose_name = _('information package')
        verbose_name_plural = _('information packages')
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
            ('see_other_user_ip_files', 'Can see files in other users IPs'),
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
            return (self.last_changed_local - self.last_changed_external).total_seconds() == 0


class EventIPManager(models.Manager):
    def from_premis_element(self, el):
        '''
        Parses a Premis event element

        Args:
            el: A lxml etree element

        Returns:
            An EventIP object describing the event
        '''

        def from_path(p):
            return '/'.join([("*[local-name()='%s']" % part) for part in p.split('/')])

        event_dict = {
            'identifier': {
                'type': el.xpath(from_path('eventIdentifier/eventIdentifierType'))[0].text,
                'value': el.xpath(from_path('eventIdentifier/eventIdentifierValue'))[0].text
            },
            'type': el.xpath(from_path('eventType'))[0].text,
            'datetime': el.xpath(from_path('eventDateTime'))[0].text,
            'detail': el.xpath(from_path('eventDetailInformation/eventDetail'))[0].text,
            'outcome_information': {
                'outcome': el.xpath(from_path('eventOutcomeInformation/eventOutcome'))[0].text,
                'outcome_detail_note': el.xpath(
                    from_path('eventOutcomeInformation/eventOutcomeDetail/eventOutcomeDetailNote')
                )[0].text,
            },
            'linking_agent_identifier': {
                'type': el.xpath(from_path('linkingAgentIdentifier/linkingAgentIdentifierType'))[0].text,
                'value': el.xpath(from_path('linkingAgentIdentifier/linkingAgentIdentifierValue'))[0].text
            },
            'linking_object_identifier': {
                'type': el.xpath(from_path('linkingObjectIdentifier/linkingObjectIdentifierType'))[0].text,
                'value': el.xpath(from_path('linkingObjectIdentifier/linkingObjectIdentifierValue'))[0].text
            },
        }

        objid = event_dict['linking_object_identifier']['value']
        username = event_dict['linking_agent_identifier']['value']

        try:
            ip = str(InformationPackage.objects.get(object_identifier_value=objid).pk)
        except InformationPackage.DoesNotExist:
            ip = objid

        event = self.model(
            eventIdentifierValue=event_dict['identifier']['value'],
            eventType_id=event_dict['type'],
            eventDateTime=event_dict['datetime'],
            eventOutcome=event_dict['outcome_information']['outcome'],
            eventOutcomeDetailNote=event_dict['outcome_information']['outcome_detail_note'] or '',
            linkingAgentIdentifierValue=username,
            linkingObjectIdentifierValue=ip,
        )
        return event

    def from_premis_file(self, xmlfile, save=True):
        root = etree.parse(xmlfile).getroot()
        events = []

        for el in root.xpath("./*[local-name()='event']"):
            event = self.from_premis_element(el)

            if EventIP.objects.filter(eventIdentifierValue=event.eventIdentifierValue).exists():
                continue

            if save:
                event.save()

            events.append(event)

        return events


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
    eventDateTime = models.DateTimeField(default=timezone.now)
    task = models.ForeignKey(
        'WorkflowEngine.ProcessTask', on_delete=models.CASCADE, null=True,
        related_name='events',
    )  # The task that generated the event
    application = models.CharField(max_length=255)
    eventVersion = models.CharField(max_length=255)  # The version number of the application (from versioneer)
    eventOutcome = models.IntegerField(choices=OUTCOME_CHOICES, null=True, default=None)  # Success (0) or Fail (1)
    eventOutcomeDetailNote = models.CharField(max_length=1024, blank=True)  # Result or traceback from IP
    linkingAgentIdentifierValue = models.CharField(max_length=255, blank=True)
    linkingAgentRole = models.CharField(max_length=255, blank=True)
    linkingObjectIdentifierValue = models.CharField(max_length=255, blank=True)
    transfer = models.ForeignKey(
        'tags.Transfer', null=True, on_delete=models.SET_NULL,
        related_name='events', verbose_name=_('transfer')
    )
    delivery = models.ForeignKey(
        'tags.Delivery', null=True, on_delete=models.SET_NULL,
        related_name='events', verbose_name=_('delivery')
    )

    objects = EventIPManager()

    class Meta:
        ordering = ["eventDateTime", "id"]
        verbose_name = 'Events related to IP'

    def __str__(self):
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
    successfully_validated = JSONField(default=None, null=True)

    @property
    def path(self):
        area_dir = Path.objects.cached('entity', self.get_type_display() + '_workarea', 'value')
        return os.path.join(area_dir, self.user.username, self.ip.object_identifier_value)

    def get_path(self):
        return self.path

    class Meta:
        ordering = ["ip"]
        unique_together = ('user', 'ip', 'type')
        permissions = (
            ('move_from_ingest_workarea', 'Can move IP from ingest workarea'),
            ('move_from_access_workarea', 'Can move IP from access workarea'),
            ('preserve_from_ingest_workarea', 'Can preserve IP from ingest workarea'),
            ('preserve_from_access_workarea', 'Can preserve IP from access workarea'),
        )


class OrderType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('order type')
        verbose_name_plural = _('order types')


class ConsignMethod(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('consign method')
        verbose_name_plural = _('consign methods')


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=255)
    responsible = models.ForeignKey('auth.User', on_delete=models.PROTECT)
    information_packages = models.ManyToManyField('ip.InformationPackage', related_name='orders', blank=True)
    type = models.ForeignKey('ip.OrderType', on_delete=models.PROTECT, null=False, verbose_name=_('type'))
    personal_number = models.CharField(max_length=255, blank=True)
    first_name = models.CharField(max_length=255, blank=True)
    family_name = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=255, blank=True)
    order_content = models.TextField(blank=True)
    consign_method = models.ForeignKey(
        'ip.ConsignMethod', on_delete=models.PROTECT, null=True, verbose_name=_('consign method')
    )

    @property
    def path(self):
        root = Path.objects.get(entity='orders').value
        return os.path.join(root, str(self.pk))

    class Meta:
        ordering = ["label"]
        permissions = (
            ('prepare_order', 'Can prepare order'),
        )
