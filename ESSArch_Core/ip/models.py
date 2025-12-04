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
import io
import logging
import os
import re
import shutil
import tarfile
import time
import uuid
import zipfile
from copy import deepcopy
from datetime import datetime
from os import walk
from pathlib import Path
from time import sleep
from urllib.parse import urljoin

import requests
from celery import states as celery_states
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import Error, OperationalError, models, transaction
from django.db.models import (
    Avg,
    CharField,
    Count,
    Exists,
    F,
    IntegerField,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
)
from django.db.models.expressions import Case, Subquery, Value, When
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from groups_manager.utils import get_permission_name
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import assign_perm
from lxml import etree
from requests import RequestException
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    stop_after_delay,
    wait_fixed,
    wait_random_exponential,
)

from ESSArch_Core.auth.models import GroupObjectsBase, Member
from ESSArch_Core.auth.util import get_group_objs_model
from ESSArch_Core.configuration.models import (
    MESSAGE_DIGEST_ALGORITHM_CHOICES,
    Path as cmPath,
)
from ESSArch_Core.crypto import encrypt_remote_credentials
from ESSArch_Core.essxml.Generator.xmlGenerator import parseContent
from ESSArch_Core.essxml.util import parse_mets
from ESSArch_Core.fixity.format import FormatIdentifier
from ESSArch_Core.fixity.receipt import AVAILABLE_RECEIPT_BACKENDS
from ESSArch_Core.managers import OrganizationManager, OrganizationQuerySet
from ESSArch_Core.profiles.models import (
    ProfileIP,
    ProfileIPData,
    SubmissionAgreement as SA,
    SubmissionAgreementIPData,
)
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.search.importers import get_backend as get_importer
from ESSArch_Core.search.ingest import index_path
from ESSArch_Core.storage.exceptions import (
    StorageMediumError,
    StorageMediumFull,
)
from ESSArch_Core.storage.models import (
    STORAGE_TARGET_STATUS_ENABLED,
    STORAGE_TARGET_STATUS_MIGRATE,
    STORAGE_TARGET_STATUS_READ_ONLY,
    StorageMedium,
    StorageMethod,
    StorageMethodTargetRelation,
    StorageObject,
    StorageTarget,
)
from ESSArch_Core.tags.documents import InformationPackageDocument
from ESSArch_Core.util import (
    delete_path,
    find_destination,
    generate_file_response,
    get_files_and_dirs,
    get_tree_size_and_count,
    in_directory,
    normalize_path,
    open_file,
    timestamp_to_datetime,
)
from ESSArch_Core.WorkflowEngine.models import ProcessTask
from ESSArch_Core.WorkflowEngine.util import create_workflow

User = get_user_model()
IP_LOCK_PREFIX = 'lock_ip_'
MB = 1024 * 1024


class AgentQuerySet(models.QuerySet):
    def with_notes(self, notes):
        qs = self.annotate(Count('notes', distinct=False)).filter(notes__count=len(notes))
        for n in notes:
            qs = qs.filter(notes__note=n)

        return qs


class AgentManager(models.Manager):
    def get_queryset(self):
        return AgentQuerySet(self.model, using=self._db)

    @retry(retry=retry_if_exception_type(OperationalError), reraise=True,
           wait=wait_random_exponential(multiplier=1, max=60),
           before_sleep=before_sleep_log(logging.getLogger('essarch'), logging.DEBUG))
    @transaction.atomic
    def from_mets_element(self, el):
        other_role = el.get("ROLE") == 'OTHER'
        other_type = el.get("TYPE") == 'OTHER'
        agent_role = el.get("OTHERROLE") if other_role else el.get("ROLE")
        agent_type = el.get("OTHERTYPE") if other_type else el.get("TYPE")
        name = el.xpath('*[local-name()="name"]')[0].text
        notes = [n.text for n in el.xpath('*[local-name()="note"]')]

        logger = logging.getLogger('essarch')
        logger.debug('try to add agent: {}, agent_typ: {}, agent_role: {}'.format(name, agent_type, agent_role))

        existing_agents_with_notes = self.model.objects.all().with_notes(notes)
        agent, created = self.model.objects.select_for_update().get_or_create(
            role=agent_role,
            type=agent_type,
            name=name,
            pk__in=existing_agents_with_notes,
            defaults={'other_role': other_role, 'other_type': other_type},
        )
        if created:
            AgentNote.objects.bulk_create(AgentNote(agent=agent, note=n) for n in notes)
        return agent

    def from_agent_dict(self, agent_dict, agent_role, agent_type):
        other_role = agent_dict.get("other_role") is True
        other_type = agent_dict.get("other_type") is True
        name = agent_dict.get('name')
        notes = agent_dict.get('notes')

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


class InformationPackageQuerySet(OrganizationQuerySet):
    def annotate_and_prefetch(self):
        def create_when(nested, celery_state):
            step_state_lookup = 'information_package__aic' if nested else 'information_package'
            return When(Exists(
                ProcessTask.objects.filter(
                    status=celery_state, **{step_state_lookup: OuterRef('pk')}
                ).values('pk')
            ), then=Value(celery_state))

        ip_tasks = ProcessTask.objects.filter(
            information_package=OuterRef('pk'),
            retried__isnull=True, steps_on_errors=None,
        ).order_by()

        return self.annotate(
            step_state=Case(
                When(package_type=InformationPackage.AIC, then=Case(
                    create_when(True, celery_states.FAILURE),
                    create_when(True, celery_states.STARTED),
                    create_when(True, celery_states.REVOKED),
                    create_when(True, celery_states.PENDING),
                    default=Value(celery_states.SUCCESS),
                    output_field=CharField(),
                )),
                default=Case(
                    create_when(False, celery_states.FAILURE),
                    create_when(False, celery_states.STARTED),
                    create_when(False, celery_states.REVOKED),
                    create_when(False, celery_states.PENDING),
                    default=Value(celery_states.SUCCESS),
                    output_field=CharField(),
                ),
                output_field=CharField(),
            ),
            status=Case(
                When(state='Prepared', then=Value(100)),
                When(
                    state='Preparing', then=Case(
                        When(submission_agreement_locked=False, then=Value(33)),
                        default=Value(66),
                        output_field=IntegerField(),
                    )
                ),
                When(
                    Exists(ip_tasks),
                    then=Subquery(
                        ip_tasks.values('information_package').annotate(sp=Avg('progress')).values('sp')[:1]
                    )
                ),
                default=Value(100),
                output_field=IntegerField(),
            ),
        ).prefetch_related(
            Prefetch('informationpackagegroupobjects_set',
                     queryset=InformationPackageGroupObjects.objects.select_related('group'), to_attr='org'),
            Prefetch(
                'submissionagreementipdata_set',
                queryset=SubmissionAgreementIPData.objects.filter(
                    pk__in=Subquery(SubmissionAgreementIPData.objects.filter(
                        information_package=OuterRef('pk'),
                        submission_agreement=OuterRef('submission_agreement'),
                    ).values('pk'))
                ),
                to_attr='submission_agreement_data_versions',
            ),
        )

    def migratable(self, export_path='', missing_storage=False, storage_methods=None, policy='',
                   include_inactive_ips=False):
        # TODO: Exclude those that already has a task that has not succeeded (?)
        if policy and not storage_methods:
            from ESSArch_Core.configuration.models import StoragePolicy
            storage_policy_obj = StoragePolicy.objects.get(pk=policy)
            storage_methods = storage_policy_obj.storage_methods.filter(
                enabled=True, storage_method_target_relations__status=STORAGE_TARGET_STATUS_ENABLED
            )
        elif not policy and not storage_methods:
            storage_methods = StorageMethod.objects.all()

        method_target_rel_with_enabled_target_without_ip = StorageMethodTargetRelation.objects.annotate(
            has_storage_obj=Exists(
                StorageObject.objects.filter(
                    storage_medium__storage_target=OuterRef('storage_target'),
                    ip=OuterRef(OuterRef('pk'))
                )
            ),
        ).filter(
            has_storage_obj=False,
            status=STORAGE_TARGET_STATUS_ENABLED,
            storage_method__in=storage_methods,
            storage_method__enabled=True,
            storage_method__storage_policies=OuterRef('submission_agreement__policy'),
        )

        def filter_objects(status):
            return StorageObject.objects.filter(
                storage_medium__storage_target__storage_method_target_relations__status=status,
                storage_medium__storage_target__storage_method_target_relations=OuterRef('pk'),
                ip=OuterRef(OuterRef('pk'))
            )

        sm_status = [STORAGE_TARGET_STATUS_MIGRATE]
        if missing_storage:
            sm_status.append(STORAGE_TARGET_STATUS_ENABLED)

        method_target_rel_with_migrate_target_with_ip = StorageMethodTargetRelation.objects.annotate(
            has_storage_obj=Exists(
                StorageObject.objects.filter(
                    storage_medium__storage_target=OuterRef('storage_target'),
                    ip=OuterRef(OuterRef('pk'))
                )
            ),
        ).filter(
            has_storage_obj=True,
            status__in=sm_status,
            storage_method__in=storage_methods,
            storage_method__enabled=True,
            storage_method__storage_policies=OuterRef('submission_agreement__policy'),
        )

        method_target_rel_with_old_migrate_and_export = StorageMethodTargetRelation.objects.none()
        if export_path:
            method_target_rel_with_old_migrate_and_export = StorageMethodTargetRelation.objects.annotate(
                has_migrate_target_with_obj=Exists(filter_objects(STORAGE_TARGET_STATUS_MIGRATE)),
            ).filter(
                has_migrate_target_with_obj=True,
                storage_method__storage_policies=OuterRef('submission_agreement__policy'),
            )

        return self.filter(
            Q(
                Q(Exists(method_target_rel_with_migrate_target_with_ip)) &
                Q(Exists(method_target_rel_with_enabled_target_without_ip)) |
                Q(Exists(method_target_rel_with_old_migrate_and_export))
            ),
            archived=True,
        ).exclude(storage=None)


class InformationPackageManager(OrganizationManager):
    def get_queryset(self):
        return InformationPackageQuerySet(self.model, using=self._db).annotate_and_prefetch()

    def visible_to_user(self, user):
        return self.for_user(user, 'view_informationpackage')

    def migratable(self, export_path='', missing_storage=False, storage_methods=None, policy='',
                   include_inactive_ips=False):
        return self.get_queryset().migratable(export_path=export_path, missing_storage=missing_storage,
                                              storage_methods=storage_methods, policy='',
                                              include_inactive_ips=include_inactive_ips)


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
        (5, '5'),
    )

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    object_identifier_value = models.CharField(_('object_identifier_value'), max_length=255, unique=True)
    label = models.CharField(_('label'), max_length=255, blank=True, db_index=True)
    content = models.CharField(max_length=255, blank=True)
    create_date = models.DateTimeField(_('create date'), default=timezone.now, db_index=True)
    state = models.CharField(_('state'), max_length=255, db_index=True)

    object_path = models.CharField(max_length=255, blank=True)
    object_size = models.BigIntegerField(_('object size'), default=0)
    object_num_items = models.IntegerField(default=0)

    start_date = models.DateTimeField(_('start date'), null=True, blank=True, db_index=True)
    end_date = models.DateTimeField(_('end date'), null=True, blank=True, db_index=True)

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

    entry_date = models.DateTimeField(_('entry date'), null=True, db_index=True)
    entry_agent_identifier_value = models.CharField(max_length=255, blank=True, db_index=True)

    package_type = models.IntegerField(_('package type'), null=True, choices=PACKAGE_TYPE_CHOICES, default=SIP)
    preservation_level_value = models.IntegerField(choices=PRESERVATION_LEVEL_VALUE_CHOICES, default=1)

    delivery_type = models.CharField(max_length=255, blank=True)
    information_class = models.IntegerField(null=True, choices=INFORMATION_CLASS_CHOICES)
    generation = models.IntegerField(null=True)

    cached = models.BooleanField(_('cached'), default=False)
    archived = models.BooleanField(_('archived'), default=False)

    last_changed_local = models.DateTimeField(auto_now=True)
    last_changed_external = models.DateTimeField(null=True)

    responsible = models.ForeignKey(
        'auth.User', verbose_name=_('responsible'), on_delete=models.SET_NULL,
        related_name='information_packages', null=True
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

    @property
    def policy(self):
        try:
            return self.submission_agreement.policy
        except AttributeError:
            return None

    def clear_lock(self):
        return cache.delete_pattern(self.get_lock_key())

    def get_lock_key(self):
        return '{}{}'.format(IP_LOCK_PREFIX, str(self.pk))

    @admin.display(boolean=True)
    def is_locked(self):
        return self.get_lock_key() in cache

    def get_permissions(self, user=User, checker=None):
        if checker is not None:
            return checker.get_perms(self)
        return user.get_all_permissions(self)

    def get_migratable_storage_methods(self):
        # Gets storage methods that the IP will be migrated to

        if not self.archived or not self.storage.exists():
            return StorageMethod.objects.none()

        return self.policy.storage_methods.annotate(
            has_object=Exists(StorageObject.objects.filter(
                ip=self, storage_medium__storage_target__methods=OuterRef('pk'),
                storage_medium__storage_target__storage_method_target_relations__status=STORAGE_TARGET_STATUS_ENABLED,
            )),
            has_enabled_rel=Exists(StorageMethodTargetRelation.objects.filter(
                status=STORAGE_TARGET_STATUS_ENABLED,
                storage_method=OuterRef('pk'),
            ))
        ).filter(enabled=True, has_object=False, has_enabled_rel=True)

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
    def change_organization(self, organization, force=False):
        group_objs_model = get_group_objs_model(self)
        group_objs_model.objects.change_organization(self, organization, force)

        from ESSArch_Core.tags.models import TagVersion
        tv_objs = TagVersion.objects.filter(tag__information_package=self)
        for tv_obj in tv_objs:
            tv_obj.change_organization(organization, force)

    def get_organization(self):
        try:
            return self.org[0]
        except AttributeError:
            return InformationPackageGroupObjects.objects.get_organization(self)
        except IndexError:
            return None

    @staticmethod
    def get_dirs(structure, data, root=""):
        for content in structure:
            if content.get('type') == 'folder':
                name = content.get('name')
                dirname = (Path(root) / name).as_posix()
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

        return created

    def create_new_generation(self, state, responsible, object_identifier_value):
        perms = deepcopy(getattr(settings, 'IP_CREATION_PERMS_MAP', {}))

        update_self = False
        if self.generation is None:
            self.generation = 0
            update_self = True
        if self.aic is None:
            self.aic = InformationPackage.objects.create(
                package_type=InformationPackage.AIC,
                responsible=self.responsible,
                label=self.label,
                start_date=self.start_date,
                end_date=self.end_date,
            )
            update_self = True
        if update_self:
            self.save()

        new_aip = deepcopy(self)
        new_aip.pk = uuid.uuid4()
        new_aip.active = True
        new_aip.object_identifier_value = new_aip.pk
        new_aip.create_date = timezone.now()
        new_aip.state = state
        new_aip.cached = False
        new_aip.archived = False
        new_aip.object_path = ''
        new_aip.responsible = responsible

        max_generation = InformationPackage.objects.filter(aic=self.aic).aggregate(
            Max('generation')
        )['generation__max']
        new_aip.generation = max_generation + 1
        new_aip.object_identifier_value = object_identifier_value or str(new_aip.pk)
        new_aip.package_mets_path = '{}.xml'.format(new_aip.object_identifier_value)
        new_aip.save()

        for profile_ip in self.profileip_set.all():
            new_profile_ip = deepcopy(profile_ip)
            new_profile_ip.pk = None
            new_profile_ip.ip = new_aip
            new_profile_ip.save()

        member = Member.objects.get(django_user=responsible)
        user_perms = perms.pop('owner', [])

        organization = responsible.user_profile.current_organization
        if organization is not None:
            organization.assign_object(new_aip, custom_permissions=perms)
            organization.add_object(new_aip)

        for perm in user_perms:
            perm_name = get_permission_name(perm, new_aip)
            assign_perm(perm_name, member.django_user, new_aip)

        return new_aip

    def get_content_type_importer_name(self):
        logger = logging.getLogger('essarch.ip')
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

    def get_content_type_file(self):
        try:
            ctsdir, ctsfile = find_destination('content_type_specification', self.get_structure(), self.object_path)
        except ProfileIP.DoesNotExist:
            return None

        if ctsdir is None:
            return None

        full_path = (Path(ctsdir) / ctsfile).as_posix()
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

        full_path = (Path(ctsdir) / ctsfile).as_posix()
        return parseContent(full_path, fill_specification_data(ip=self, ignore=['_CTS_PATH', '_CTS_SCHEMA_PATH']))

    def get_doc(self):
        return InformationPackageDocument.get(id=str(self.pk))

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
        ip = self.related_ips(cached=False).filter(archived=False).first()

        if ip is not None:
            return ip.workareas.first()

        return None

    def create_profile_rels(self, profile_types, user, profileips_data=None):
        sa = self.submission_agreement
        extra_data = fill_specification_data(ip=self, sa=sa)
        for p_type in profile_types:
            if ProfileIP.objects.filter(ip=self, profile__profile_type=p_type).exists() and not profileips_data:
                continue
            profile = getattr(sa, 'profile_%s' % p_type, None)

            if profile is None:
                continue

            pi_data = {}
            for profileip_data in (profileips_data or []):
                if profileip_data.get('profile_type') == p_type:
                    pi_data = profileip_data
                    pi_data['data'].pop('relation', None)
                    pi_data['data'].pop('user', None)
                    break

            id = pi_data.get('id', uuid.uuid4())
            profile_ip, _ = ProfileIP.objects.update_or_create(id=id, defaults={
                'ip': self,
                'profile': profile
            })

            if not pi_data:
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

                data_obj = ProfileIPData.objects.create(
                    relation=profile_ip,
                    data=data,
                    version=0,
                    user=user
                )
            else:
                data_obj, _ = ProfileIPData.objects.update_or_create(
                    id=pi_data['data']['id'],
                    relation=profile_ip,
                    user=user,
                    defaults=pi_data['data'],
                )
            profile_ip.data = data_obj
            profile_ip.save()

    @retry(retry=retry_if_exception_type(Error), reraise=True, stop=stop_after_delay(300),
           wait=wait_random_exponential(multiplier=1, max=10),
           before_sleep=before_sleep_log(logging.getLogger('essarch'), logging.WARNING))
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

    @retry(retry=retry_if_exception_type(Error), reraise=True, stop=stop_after_delay(300),
           wait=wait_random_exponential(multiplier=1, max=10),
           before_sleep=before_sleep_log(logging.getLogger('essarch'), logging.WARNING))
    def get_profile(self, profile_type):
        try:
            return self.get_profile_rel(profile_type).profile
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
        except Exception:
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
        except Exception:
            return None

    def get_allow_unknown_file_types(self):
        profile_type = self.get_package_type_display().lower()
        allow_unknown_file_types = self.get_profile_data(profile_type).get('allow_unknown_file_types', False)
        if allow_unknown_file_types is True or allow_unknown_file_types == 'True':
            return True
        return False

    def get_allow_encrypted_files(self):
        profile_type = self.get_package_type_display().lower()
        allow_encrypted_files = self.get_profile_data(profile_type).get('allow_encrypted_files', False)
        if allow_encrypted_files is True or allow_encrypted_files == 'True':
            return True
        return False

    def get_structure(self):
        ip_profile_type = self.get_package_type_display().lower()
        ip_profile_rel = self.get_profile_rel(ip_profile_type)
        return ip_profile_rel.profile.structure

    def get_content_mets_file_path(self):
        mets_dir, mets_name = find_destination("mets_file", self.get_structure())
        if mets_dir is not None:
            path = (Path(mets_dir) / mets_name).as_posix()
            path = parseContent(path, fill_specification_data(ip=self))
        else:
            path = 'mets.xml'

        return normalize_path(path)

    def get_premis_file_path(self):
        try:
            premis_dir, premis_name = find_destination("preservation_description_file", self.get_structure())
        except ProfileIP.DoesNotExist:
            return None

        if premis_dir is not None:
            path = (Path(premis_dir) / premis_name).as_posix()
        else:
            path = 'metadata/premis.xml'

        return normalize_path(path)

    def get_events_file_path(self, from_container=False):
        if not from_container and os.path.isfile(self.object_path):
            return os.path.splitext(self.object_path)[0] + '_ipevents.xml'

        ip_profile = self.get_profile(self.get_package_type_display().lower())
        structure = ip_profile.structure

        events_dir, events_file = find_destination('events_file', structure)
        if events_dir is not None:
            full_path = (Path(events_dir) / events_file).as_posix()
            return normalize_path(parseContent(full_path, fill_specification_data(ip=self)))

        return 'ipevents.xml'

    def update_sip_data(self):
        sip_profile = self.submission_agreement.profile_sip
        if sip_profile is not None and self.sip_path is not None:
            sip_mets_dir, sip_mets_file = find_destination('mets_file', sip_profile.structure, self.sip_path)
            if os.path.isfile(self.sip_path):
                sip_mets_data = parse_mets(
                    open_file(
                        os.path.join(self.object_path, sip_mets_dir, sip_mets_file), 'rb',
                        container=self.sip_path,
                        container_prefix=self.object_identifier_value,
                    )
                )
            else:
                try:
                    sip_mets_data = parse_mets(
                        open_file(
                            os.path.join(self.object_path, sip_mets_dir, sip_mets_file), 'rb',
                        )
                    )
                except FileNotFoundError:
                    sip_mets_data = {}
                    pass

            # prefix all SIP data
            sip_mets_data = {f'SIP_{k.upper()}': v for k, v in sip_mets_data.items()}

            aip_profile_rel_data = self.get_profile_rel('aip').data
            aip_profile_rel_data.data.update(sip_mets_data)
            aip_profile_rel_data.save()

    def update_ip_profile_rel_data(self, profile_rel_data, profile_type='aip'):
        ip_profile_rel_data = self.get_profile_rel(profile_type).data
        ip_profile_rel_data.data.update(profile_rel_data)
        ip_profile_rel_data.save()

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

    def list_files(self, path='', fileobj=None, expand_container=False):
        fullpath = os.path.join(self.object_path, path).rstrip('/')
        if os.path.basename(self.object_path) == path and os.path.isfile(self.object_path):
            if expand_container and tarfile.is_tarfile(self.object_path):
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

            elif expand_container and zipfile.is_zipfile(self.object_path) and \
                    os.path.splitext(self.object_path)[1] == '.zip':
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

        if expand_container and os.path.isfile(fullpath) and tarfile.is_tarfile(fullpath):
            with tarfile.open(fullpath) as tar:
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

        elif expand_container and os.path.isfile(fullpath) and zipfile.is_zipfile(fullpath) and \
                os.path.splitext(fullpath)[1] == '.zip':
            with zipfile.ZipFile(fullpath) as zipf:
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

        elif expand_container and fileobj and tarfile.is_tarfile(fileobj):
            with tarfile.open(fileobj=fileobj) as tar:
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

        elif expand_container and fileobj and zipfile.is_zipfile(fileobj):
            with zipfile.ZipFile(fileobj) as zipf:
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
            raise ValidationError('Illegal path: {}'.format(path))

    def get_path_response(self, path, request, force_download=False, expand_container=False, paginator=None):
        self.validate_path(path)
        if not expand_container:
            try:
                if not path:
                    raise OSError(errno.EISDIR, os.strerror(errno.EISDIR), path)

                if os.path.isfile(self.object_path):
                    container_path = os.path.join(os.path.dirname(self.object_path), path.split('/', 1)[0])
                    container_path = normalize_path(container_path)
                    if container_path == self.object_path:
                        path = path.split('/', 1)[1]

                fid = FormatIdentifier(allow_unknown_file_types=True)

                if len(path.split('.tar/')) == 2:
                    tar_path, tar_subpath = path.split('.tar/')
                    tar_path += '.tar'

                    with tarfile.open(fileobj=self.open_file(tar_path, 'rb')) as tar:
                        try:
                            f = io.BytesIO(tar.extractfile(tar_subpath).read())
                            content_type = fid.get_mimetype(tar_subpath)
                            return generate_file_response(f, content_type, force_download, name=tar_subpath)
                        except KeyError:
                            raise NotFound

                if len(path.split('.zip/')) == 2:
                    zip_path, zip_subpath = path.split('.zip/')
                    zip_path += '.zip'

                    with zipfile.ZipFile(self.open_file(zip_path, 'rb')) as zipf:
                        try:
                            f = io.BytesIO(zipf.read(zip_subpath))
                            content_type = fid.get_mimetype(zip_subpath)
                            return generate_file_response(f, content_type, force_download, name=zip_subpath)
                        except KeyError:
                            raise NotFound

                content_type = fid.get_mimetype(path)
                return generate_file_response(
                    self.open_file(path, 'rb'),
                    content_type,
                    force_download=force_download,
                    name=path
                )
            except OSError as e:
                if e.errno == errno.ENOENT:
                    raise NotFound

                # Windows raises PermissionDenied (errno.EACCES) when trying to use
                # open() on a directory
                if os.name == 'nt':
                    if e.errno not in (errno.EACCES, errno.EISDIR):
                        raise
                elif e.errno != errno.EISDIR:
                    raise
            except IndexError:
                if force_download or not expand_container:
                    fid = FormatIdentifier(allow_unknown_file_types=True)
                    content_type = fid.get_mimetype(path)
                    return generate_file_response(
                        self.open_file(self.object_path, 'rb'),
                        content_type,
                        force_download=force_download,
                        name=path
                    )

        entries = self.list_files(path, expand_container=expand_container)
        if paginator is not None:
            paginated = paginator.paginate_queryset(entries, request)
            return paginator.get_paginated_response(paginated)
        return Response(entries)

    def create_preservation_workflow(self):
        container_methods = self.policy.storage_methods.secure_storage().filter(remote=False)
        non_container_methods = self.policy.storage_methods.archival_storage().filter(remote=False)
        remote_methods = self.policy.storage_methods.filter(remote=True)
        generate_aic = self.profile_locked('aic_description')

        remote_servers = set([
            method.enabled_target.remote_server
            for method in remote_methods
        ])

        profile_type = self.get_package_type_display().lower()
        index_files = self.get_profile_data(profile_type).get('index_files', True)
        index_files_content = self.get_profile_data(profile_type).get('index_files_content', True)
        index_cits = self.get_profile_data(profile_type).get('index_cits', True)
        if (index_files is True or index_files == 'True' or
                index_files_content is True or index_files_content == 'True' or
                index_cits is True or index_cits == 'True'):
            write_to_search_index = True
        else:
            write_to_search_index = False

        remote_temp_container_transfer = {
            "step": True,
            "parallel": True,
            "name": "Write temporary files to remote hosts",
            "children": [
                {
                    "step": True,
                    "parallel": True,
                    "name": "Write temporary files to remote host ({})".format(remote_server.split(',')[0]),
                    "children": [
                        {
                            "name": "ESSArch_Core.tasks.CopyFile",
                            "label": "Transfer temporary container",
                            "args": ["{{TEMP_CONTAINER_PATH}}"],
                            "params": {
                                "remote_host": remote_server.split(',')[0],
                                "remote_credentials": encrypt_remote_credentials(remote_server),
                            },
                        },
                        {
                            "name": "ESSArch_Core.tasks.CopyFile",
                            "label": "Transfer temporary AIP xml",
                            "args": ["{{TEMP_METS_PATH}}"],
                            "params": {
                                "remote_host": remote_server.split(',')[0],
                                "remote_credentials": encrypt_remote_credentials(remote_server),
                            },
                        },
                        {
                            "name": "ESSArch_Core.tasks.CopyFile",
                            "run_if": "{{TEMP_AIC_METS_PATH}}",
                            "label": "Transfer temporary AIC xml",
                            "args": ["{{TEMP_AIC_METS_PATH}}"],
                            "params": {
                                "remote_host": remote_server.split(',')[0],
                                "remote_credentials": encrypt_remote_credentials(remote_server),
                            },
                        },
                    ]
                } for remote_server in remote_servers
            ]
        }

        remote_temp_container_to_storage_method = {
            "step": True,
            "parallel": True,
            "name": "Write temporary container to storage on remote hosts",
            "children": [
                {
                    "step": True,
                    "parallel": True,
                    "name": "Write container to storage on remote host ({})".format(remote_server.split(',')[0]),
                    "children": [
                        {
                            "name": "ESSArch_Core.ip.tasks.PreserveInformationPackage",
                            "label": "Write to storage method ({})".format(method.name),
                            "args": [str(method.pk)],
                        } for method in remote_methods
                    ]
                } for remote_server in remote_servers
            ]
        }

        remote_temp_container_delete = {
            "step": True,
            "parallel": True,
            "name": "Delete temporary files on remote hosts",
            "children": [
                {
                    "step": True,
                    "parallel": True,
                    "name": "Delete temporary files on remote host ({})".format(remote_server.split(',')[0]),
                    "children": [
                        {
                            "name": "ESSArch_Core.tasks.DeleteFiles",
                            "label": "Delete temporary container",
                            "args": ["{{TEMP_CONTAINER_PATH}}"],
                            "params": {
                                "remote_host": remote_server.split(',')[0],
                                "remote_credentials": encrypt_remote_credentials(remote_server),
                            },
                        },
                        {
                            "name": "ESSArch_Core.tasks.DeleteFiles",
                            "label": "Delete temporary AIP xml",
                            "args": ["{{TEMP_METS_PATH}}"],
                            "params": {
                                "remote_host": remote_server.split(',')[0],
                                "remote_credentials": encrypt_remote_credentials(remote_server),
                            },
                        },
                        {
                            "name": "ESSArch_Core.tasks.DeleteFiles",
                            "run_if": "{{TEMP_AIC_METS_PATH}}",
                            "label": "Delete temporary AIC xml",
                            "args": ["{{TEMP_AIC_METS_PATH}}"],
                            "params": {
                                "remote_host": remote_server.split(',')[0],
                                "remote_credentials": encrypt_remote_credentials(remote_server),
                            },
                        },
                    ]
                } for remote_server in remote_servers
            ]
        }

        remote_servers_archived = {
            "step": True,
            "parallel": True,
            "name": "Mark as archived on remote hosts",
            "children": [
                {
                    "step": True,
                    "parallel": True,
                    "name": "Mark as archived on remote host ({})".format(remote_server.split(',')[0]),
                    "children": [
                        {
                            "name": "ESSArch_Core.ip.tasks.MarkArchived",
                            "label": "Mark as archived",
                            "params": {
                                "remote_host": remote_server.split(',')[0],
                                "remote_credentials": encrypt_remote_credentials(remote_server),
                            },
                        },
                    ]
                } for remote_server in remote_servers
            ]
        }

        remote_containers_step = {
            "step": True,
            "name": "Write remote containers",
            "children": [
                remote_temp_container_transfer,
                remote_temp_container_to_storage_method,
                remote_temp_container_delete,
                remote_servers_archived,
            ],
        }

        workflow = [
            {
                "step": True,
                "name": "Write to storage",
                "children": [
                    {
                        "step": True,
                        "name": "Write to search index",
                        "children": [
                            {
                                "name": "ESSArch_Core.ip.tasks.WriteInformationPackageToSearchIndex",
                                "label": "Write to search index",
                                "if": write_to_search_index,
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
                                        "label": "Write to storage method ({})".format(method.name),
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
                                        "if": generate_aic,
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
                                                        "label": "Write to storage method ({})".format(method.name),
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
                                    {
                                        "name": "ESSArch_Core.tasks.DeleteFiles",
                                        "label": "Delete temporary mets",
                                        "args": ["{{TEMP_METS_PATH}}"]
                                    },
                                    {
                                        "name": "ESSArch_Core.tasks.DeleteFiles",
                                        "if": generate_aic,
                                        "label": "Delete temporary aic mets",
                                        "args": ["{{TEMP_AIC_METS_PATH}}"]
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
                "name": "ESSArch_Core.ip.tasks.PostPreservationCleanup",
                "label": "Clean up workflow files",
            },
        ]

        return workflow

    def create_access_workflow(self, user, tar=False, extracted=False, new=False, object_identifier_value=None,
                               package_xml=False, aic_xml=False, diff_check=False, edit=False, responsible=None):
        logger = logging.getLogger('essarch.ip')
        if new:
            dst_object_identifier_value = object_identifier_value or str(uuid.uuid4())
        else:
            dst_object_identifier_value = self.object_identifier_value

        if aic_xml and self.aic is None:
            logger.warning('User: {} requested access of AIC xml, IP: {} does not have any AIC'.format(
                user.username, self.object_identifier_value))
            aic_xml = False

        if not self.archived:
            ingest_workarea = cmPath.objects.get(entity='ingest_workarea').value
            container = os.path.isfile(self.object_path)
            ingest_workarea_user = (Path(ingest_workarea) / user.username / dst_object_identifier_value).as_posix()
            ingest_workarea_user_extracted = (Path(ingest_workarea_user) / dst_object_identifier_value).as_posix()

            workflow = [
                {
                    "name": "ESSArch_Core.tasks.ExtractTAR",
                    "label": "Extract container to workspace",
                    "if": container and extracted,
                    "args": [
                        self.object_path,
                        ingest_workarea_user,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.CopyFile",
                    "label": "Copy information package to workspace",
                    "if": container and not extracted,
                    "args": [
                        self.object_path,
                        ingest_workarea_user,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.CopyDir",
                    "label": "Copy information package to workspace",
                    "if": not container,
                    "args": [
                        self.object_path,
                        ingest_workarea_user_extracted,
                    ],
                },
            ]

            if new:
                new_aip = self.create_new_generation('Ingest Workspace', user, dst_object_identifier_value)
                new_aip.object_path = ingest_workarea_user_extracted
                new_aip.save()

            elif edit:
                new_aip = self

                workflow.extend([
                    {
                        "name": "ESSArch_Core.tasks.DeleteFiles",
                        "label": "Delete from ingest",
                        "args": [self.object_path]
                    },
                    {
                        "name": "ESSArch_Core.tasks.UpdateIPPath",
                        "label": "Update IP path",
                        "args": [ingest_workarea_user_extracted],
                    },
                    {
                        "name": "ESSArch_Core.tasks.UpdateIPStatus",
                        "label": "Set status to Ingest Workspace",
                        "args": ["Ingest Workspace"],
                    },
                ])

            else:
                new_aip = self

            workflow.append(
                {
                    "name": "ESSArch_Core.ip.tasks.CreateWorkarea",
                    "label": "Create workspace",
                    "args": [str(new_aip.pk), str(user.pk), Workarea.INGEST, not new and not edit]
                }
            )

            return create_workflow(workflow, self, name='Access Information Package', responsible=responsible)

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

        if storage_object.content_location_type == 300:
            worker_queue = 'io_tape'
        else:
            worker_queue = 'io_disk'

        cache_storage = self.policy.cache_storage
        cache_target = None
        if cache_storage is not None:
            try:
                cache_enabled_target = cache_storage.enabled_target
                if cache_enabled_target.storagemedium_set.writeable().exists():
                    cache_target = cache_enabled_target.target
            except StorageTarget.DoesNotExist:
                pass

        temp_dir = cmPath.objects.get(entity='temp').value
        temp_object_path = self.get_temp_object_path()
        temp_container_path = self.get_temp_container_path()
        temp_mets_path = self.get_temp_container_xml_path()
        temp_aic_mets_path = self.get_temp_container_aic_xml_path() if self.aic else None

        storage_medium = storage_object.storage_medium
        storage_target = storage_medium.storage_target
        storage_method = storage_target.methods.first()

        access_workarea = cmPath.objects.get(entity='access_workarea').value
        access_workarea_user = (Path(access_workarea) / user.username / dst_object_identifier_value).as_posix()
        access_workarea_user_extracted = (Path(access_workarea_user) / dst_object_identifier_value).as_posix()
        access_workarea_user_container = (Path(access_workarea_user) / '{}.{}'.format(
            self.object_identifier_value, self.get_container_format().lower())).as_posix()
        access_workarea_user_package_xml = (Path(access_workarea_user) / self.package_mets_path.split('/')[-1]
                                            ).as_posix()
        access_workarea_user_extracted_content_xml = (Path(access_workarea_user_extracted) / self.content_mets_path
                                                      ).as_posix() if self.content_mets_path else None
        access_workarea_user_aic_xml = (Path(access_workarea_user) / f'{self.aic.object_identifier_value}.xml'
                                        ).as_posix() if aic_xml else None

        if new:
            new_aip = self.create_new_generation('Access Workarea', user, dst_object_identifier_value)
            new_aip.object_path = access_workarea_user_extracted
            new_aip.save()
            access_workarea_user_extracted_src = (Path(access_workarea_user) / self.object_identifier_value).as_posix()
        else:
            access_workarea_user_extracted_src = None
            new_aip = self

        os.makedirs(access_workarea_user, exist_ok=True)

        if storage_target.remote_server:
            # AccessAIP instructs and waits for ip.access to transfer files from remote
            # to master. Then we use CopyFile to copy files from local temp to workspace

            workflow = [
                {
                    "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                    "label": "Access AIP from remote host ({})".format(storage_target.remote_server.split(',')[0]),
                    "queue": worker_queue,
                    "args": [str(self.pk)],
                    "params": {
                        "storage_object": str(storage_object.pk),
                        'dst': temp_dir,
                        'local': False,
                    },
                },
                {
                    "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                    "if": diff_check and tar,
                    "label": "Redundancy check against package-mets",
                    "queue": worker_queue,
                    "args": [
                        temp_container_path,
                        temp_mets_path,
                        [(Path(dst_object_identifier_value) / self.content_mets_path).as_posix(),
                         self.content_mets_path]
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.ExtractTAR",
                    "label": "Extract temporary container to cache",
                    "queue": worker_queue,
                    "if": storage_method.cached and cache_target is not None,
                    "allow_failure": True,
                    "args": [
                        temp_container_path,
                        cache_target,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.ExtractTAR",
                    "label": "Extract temporary container to workspace",
                    "queue": worker_queue,
                    "if": extracted,
                    "args": [
                        temp_container_path,
                        access_workarea_user,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                    "if": diff_check and extracted,
                    "label": "Redundancy check against content-mets",
                    "queue": worker_queue,
                    "args": [
                        access_workarea_user_extracted,
                        access_workarea_user_extracted_content_xml
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.CopyFile",
                    "label": "Copy temporary container to workspace",
                    "queue": worker_queue,
                    "if": tar,
                    "args": [
                        temp_container_path,
                        access_workarea_user_container,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.CopyFile",
                    "label": "Copy temporary AIP xml to workspace",
                    "queue": worker_queue,
                    "if": tar and package_xml,
                    "args": [
                        temp_mets_path,
                        access_workarea_user_package_xml,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.CopyFile",
                    "label": "Copy temporary AIC xml to workspace",
                    "queue": worker_queue,
                    "if": tar and aic_xml,
                    "args": [
                        temp_aic_mets_path,
                        access_workarea_user_aic_xml,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.DeleteFiles",
                    "label": "Delete temporary container",
                    "queue": worker_queue,
                    "args": [temp_container_path]
                },
                {
                    "name": "ESSArch_Core.tasks.DeleteFiles",
                    "label": "Delete temporary AIP xml",
                    "queue": worker_queue,
                    "args": [temp_mets_path]
                },
                {
                    "name": "ESSArch_Core.tasks.DeleteFiles",
                    "label": "Delete temporary AIC xml",
                    "queue": worker_queue,
                    "if": aic_xml,
                    "args": [temp_aic_mets_path]
                },
            ]
        else:
            if is_cached_storage_object:
                workflow = [
                    {
                        "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                        "label": "Access AIP",
                        "queue": worker_queue,
                        "if": extracted,
                        "args": [str(self.pk)],
                        "params": {
                            "storage_object": str(storage_object.pk),
                            'dst': access_workarea_user_extracted
                        },
                    },
                    {
                        "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                        "if": diff_check and extracted,
                        "label": "Redundancy check against content-mets",
                        "queue": worker_queue,
                        "args": [
                            access_workarea_user_extracted,
                            access_workarea_user_extracted_content_xml
                        ],
                    },
                    {
                        "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                        "label": "Access AIP",
                        "queue": worker_queue,
                        "if": tar,
                        "args": [str(self.pk)],
                        "params": {
                            "storage_object": str(storage_object.pk),
                            'dst': temp_object_path,
                        },
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.CreateContainer",
                        "label": "Create temporary container",
                        "queue": worker_queue,
                        "if": tar,
                        "args": [temp_object_path, access_workarea_user_container],
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.GeneratePackageMets",
                        "label": "Create container mets",
                        "queue": worker_queue,
                        "if": tar and package_xml,
                        "args": [
                            access_workarea_user_container,
                            access_workarea_user_package_xml,
                        ]
                    },
                    {
                        "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                        "if": diff_check and tar,
                        "label": "Redundancy check against package-mets",
                        "queue": worker_queue,
                        "args": [
                            access_workarea_user_container,
                            access_workarea_user_package_xml,
                            [(Path(dst_object_identifier_value) / self.content_mets_path).as_posix(),
                             self.content_mets_path]
                        ],
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.GenerateAICMets",
                        "label": "Create container aic mets",
                        "queue": worker_queue,
                        "if": aic_xml,
                        "args": [access_workarea_user_aic_xml]
                    },
                    {
                        "name": "ESSArch_Core.tasks.DeleteFiles",
                        "label": "Delete temporary object",
                        "queue": worker_queue,
                        "args": [temp_object_path]
                    },
                ]

            elif storage_object.container:
                # reading from long-term storage

                workflow = [
                    {
                        "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                        "label": "Access AIP",
                        "queue": worker_queue,
                        "args": [str(self.pk)],
                        "params": {
                            "storage_object": str(storage_object.pk),
                            'dst': temp_dir,
                        },
                    },
                    {
                        "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                        "if": diff_check and tar,
                        "label": "Redundancy check against package-mets",
                        "queue": worker_queue,
                        "args": [
                            temp_container_path,
                            temp_mets_path,
                            [(Path(dst_object_identifier_value) / self.content_mets_path).as_posix(),
                             self.content_mets_path]
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.ExtractTAR",
                        "label": "Extract temporary container to cache",
                        "queue": worker_queue,
                        "if": storage_method.cached and cache_target is not None,
                        "allow_failure": True,
                        "args": [
                            temp_container_path,
                            cache_target,
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.ExtractTAR",
                        "label": "Extract temporary container to workspace",
                        "queue": worker_queue,
                        "if": extracted,
                        "args": [
                            temp_container_path,
                            access_workarea_user,
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                        "if": diff_check and extracted,
                        "label": "Redundancy check against content-mets",
                        "queue": worker_queue,
                        "args": [
                            access_workarea_user_extracted,
                            access_workarea_user_extracted_content_xml
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.MoveDir",
                        "label": "Rename workspace to new generation",
                        "queue": worker_queue,
                        "if": extracted and new,
                        "args": [
                            access_workarea_user_extracted_src,
                            access_workarea_user_extracted,
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.CopyFile",
                        "label": "Copy temporary container to workspace",
                        "queue": worker_queue,
                        "if": tar,
                        "args": [
                            temp_container_path,
                            access_workarea_user_container,
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.CopyFile",
                        "label": "Copy temporary AIP xml to workspace",
                        "queue": worker_queue,
                        "if": package_xml,
                        "args": [
                            temp_mets_path,
                            access_workarea_user_package_xml,
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.CopyFile",
                        "label": "Copy temporary AIC xml to workspace",
                        "queue": worker_queue,
                        "if": aic_xml,
                        "args": [
                            temp_aic_mets_path,
                            access_workarea_user_aic_xml,
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.DeleteFiles",
                        "label": "Delete temporary container",
                        "queue": worker_queue,
                        "args": [temp_container_path]
                    },
                    {
                        "name": "ESSArch_Core.tasks.DeleteFiles",
                        "label": "Delete temporary AIP xml",
                        "queue": worker_queue,
                        "args": [temp_mets_path]
                    },
                    {
                        "name": "ESSArch_Core.tasks.DeleteFiles",
                        "label": "Delete temporary AIC xml",
                        "queue": worker_queue,
                        "if": temp_aic_mets_path,
                        "args": [temp_aic_mets_path]
                    },
                ]
            else:
                # reading from non long-term storage
                if cache_target is not None:
                    cache_dst = (Path(cache_target) / self.object_identifier_value).as_posix()
                else:
                    cache_dst = None

                workflow = [
                    {
                        "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                        "label": "Copy AIP to cache",
                        "queue": worker_queue,
                        "if": storage_method.cached and cache_dst is not None,
                        "allow_failure": True,
                        "args": [str(self.pk)],
                        "params": {
                            "storage_object": str(storage_object.pk),
                            "dst": cache_dst,
                        },
                    },
                    {
                        "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                        "label": "Access AIP",
                        "queue": worker_queue,
                        "if": extracted,
                        "args": [str(self.pk)],
                        "params": {
                            "storage_object": str(storage_object.pk),
                            'dst': access_workarea_user_extracted
                        },
                    },
                    {
                        "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                        "if": diff_check and extracted,
                        "label": "Redundancy check against content-mets",
                        "queue": worker_queue,
                        "args": [
                            access_workarea_user_extracted,
                            access_workarea_user_extracted_content_xml
                        ],
                    },
                    {
                        "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                        "label": "Access AIP",
                        "queue": worker_queue,
                        "if": tar,
                        "args": [str(self.pk)],
                        "params": {
                            "storage_object": str(storage_object.pk),
                            'dst': temp_object_path,
                        },
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.CreateContainer",
                        "label": "Create temporary container",
                        "queue": worker_queue,
                        "if": tar,
                        "args": [temp_object_path, access_workarea_user_container],
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.GeneratePackageMets",
                        "label": "Create container mets",
                        "queue": worker_queue,
                        "if": tar and package_xml,
                        "args": [
                            access_workarea_user_container,
                            access_workarea_user_package_xml,
                        ]
                    },
                    {
                        "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                        "if": diff_check and tar,
                        "label": "Redundancy check against package-mets",
                        "queue": worker_queue,
                        "args": [
                            access_workarea_user_container,
                            access_workarea_user_package_xml,
                            [(Path(dst_object_identifier_value) / self.content_mets_path).as_posix(),
                             self.content_mets_path]
                        ],
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.GenerateAICMets",
                        "label": "Create container aic mets",
                        "queue": worker_queue,
                        "if": aic_xml,
                        "args": [access_workarea_user_aic_xml]
                    },
                    {
                        "name": "ESSArch_Core.tasks.DeleteFiles",
                        "label": "Delete temporary object",
                        "queue": worker_queue,
                        "args": [temp_object_path]
                    },
                ]

        workflow.append({
            "name": "ESSArch_Core.ip.tasks.CreateWorkarea",
            "label": "Create workarea",
            "queue": worker_queue,
            "args": [str(new_aip.pk), str(user.pk), Workarea.ACCESS, tar]
        })
        return create_workflow(workflow, self, name='Access Information Package', responsible=responsible)

    def create_migration_workflow(self, temp_path, storage_methods, export_path='', tar=False, extracted=False,
                                  package_xml=False, aic_xml=False, diff_check=True, responsible=None,
                                  top_root_step=None):

        logger = logging.getLogger('essarch.ip')
        container_methods = self.policy.storage_methods.secure_storage().filter(
            remote=False, pk__in=storage_methods)
        non_container_methods = self.policy.storage_methods.archival_storage().filter(
            remote=False, pk__in=storage_methods)
        # remote_methods = self.policy.storage_methods.filter(
        #     remote=True, pk__in=storage_methods)

        dst_object_identifier_value = self.object_identifier_value

        aic_xml = True if self.aic else False

        migration_receipt = 'api_ip_migrated' in AVAILABLE_RECEIPT_BACKENDS.keys()

        if container_methods.exists() or tar:
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

        if storage_object.storage_medium.format <= 101:
            diff_check = False

        is_cached_storage_object = storage_object.is_cache_for_ip(self)

        if storage_object.content_location_type == 300:
            worker_queue = 'io_tape'
            worker_queue_1 = 'io_tape_1'
        else:
            worker_queue = 'io_disk'
            worker_queue_1 = 'io_disk'

        # cache_storage = self.policy.cache_storage
        # cache_target = None
        # if cache_storage is not None:
        #     try:
        #         cache_enabled_target = cache_storage.enabled_target
        #         if cache_enabled_target.storagemedium_set.writeable().exists():
        #             cache_target = cache_enabled_target.target
        #     except StorageTarget.DoesNotExist:
        #         pass

        temp_path = temp_path if temp_path else cmPath.objects.get(entity='temp').value
        temp_object_path = self.get_temp_object_path(temp_path)  # dir_path
        temp_container_path = self.get_temp_container_path(temp_path)  # container_path
        temp_mets_path = self.get_temp_container_xml_path(temp_path)  # aip_xml_path
        temp_aic_mets_path = self.get_temp_container_aic_xml_path(temp_path) if self.aic else None  # aic_xml_path

        storage_medium = storage_object.storage_medium
        storage_target = storage_medium.storage_target
        # storage_method = storage_target.methods.first()

        export_path_dst = (Path(export_path) / dst_object_identifier_value).as_posix()
        export_path_dst_extracted = (Path(export_path_dst) / dst_object_identifier_value).as_posix()
        export_path_dst_container = (Path(export_path_dst) / '{}.{}'.format(
            self.object_identifier_value, self.get_container_format().lower())).as_posix()
        export_path_dst_package_xml = (Path(export_path_dst) / self.package_mets_path.split('/')[-1]
                                       ).as_posix()
        export_path_dst_extracted_content_xml = (Path(export_path_dst_extracted) / self.content_mets_path
                                                 ).as_posix() if self.content_mets_path else None
        export_path_dst_aic_xml = (Path(export_path_dst) / f'{self.aic.object_identifier_value}.xml'
                                   ).as_posix() if aic_xml else None

        # access_workarea = cmPath.objects.get(entity='access_workarea').value
        # access_workarea_user = os.path.join(access_workarea, user.username, dst_object_identifier_value)
        # access_workarea_user = os.path.join(access_workarea, 'superuser', dst_object_identifier_value)
        # access_workarea_user_extracted = os.path.join(access_workarea_user, dst_object_identifier_value)
        # access_workarea_user_container = os.path.join(access_workarea_user, '{}.{}'.format(
        #    self.object_identifier_value, self.get_container_format().lower()))
        # access_workarea_user_package_xml = os.path.join(access_workarea_user, self.package_mets_path.split('/')[-1])
        # access_workarea_user_extracted_content_xml = os.path.join(
        #    access_workarea_user_extracted, self.content_mets_path) if self.content_mets_path else None
        # if aic_xml:
        #    access_workarea_user_aic_xml = os.path.join(access_workarea_user,
        #                                                self.aic.object_identifier_value) + '.xml'
        # else:
        #    access_workarea_user_aic_xml = None

        # access_workarea_user_extracted_src = None
        # new_aip = self

        if export_path:
            os.makedirs(export_path_dst, exist_ok=True)

        if storage_target.remote_server:
            # AccessAIP instructs and waits for ip.access to transfer files from remote
            # to master. Then we use CopyFile to copy files from local temp to workspace

            workflow = [
                {
                    "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                    "label": "Access AIP",
                    "queue": worker_queue_1,
                    "args": [str(self.pk)],
                    "params": {
                        "storage_object": str(storage_object.pk),
                        'dst': temp_path,
                        'local': False,
                    },
                },
                {
                    "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                    "if": diff_check and tar,
                    "label": "Redundancy check against package-mets",
                    "queue": worker_queue,
                    "args": [
                        temp_container_path,
                        temp_mets_path,
                        [(Path(dst_object_identifier_value) / self.content_mets_path).as_posix(),
                         self.content_mets_path]
                    ],
                },
                # {
                #     "name": "ESSArch_Core.tasks.ExtractTAR",
                #     "label": "Extract temporary container to cache",
                #     "queue": worker_queue,
                #     "if": storage_method.cached and cache_target is not None,
                #     "allow_failure": True,
                #     "args": [
                #         temp_container_path,
                #         cache_target,
                #     ],
                # },
                {
                    "name": "ESSArch_Core.tasks.ExtractTAR",
                    "label": "Extract temporary container to export",
                    "queue": worker_queue,
                    "if": extracted and export_path,
                    "args": [
                        temp_container_path,
                        export_path_dst,
                    ],
                },
                # {
                #     "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                #     "if": diff_check and extracted,
                #     "label": "Redundancy check against content-mets",
                #     "queue": worker_queue,
                #     "args": [
                #         access_workarea_user_extracted,
                #         access_workarea_user_extracted_content_xml
                #     ],
                # },
                {
                    "name": "ESSArch_Core.tasks.CopyFile",
                    "label": "Copy temporary container to export",
                    "queue": worker_queue,
                    "if": tar and export_path,
                    "args": [
                        temp_container_path,
                        export_path_dst_container,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.CopyFile",
                    "label": "Copy temporary AIP xml to export",
                    "queue": worker_queue,
                    "if": tar and package_xml and export_path,
                    "args": [
                        temp_mets_path,
                        export_path_dst_package_xml,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.CopyFile",
                    "label": "Copy temporary AIC xml to export",
                    "queue": worker_queue,
                    "if": tar and aic_xml and export_path,
                    "args": [
                        temp_aic_mets_path,
                        export_path_dst_aic_xml,
                    ],
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
                                    "label": "Write to storage method ({})".format(method.name),
                                    "queue": worker_queue,
                                    "args": [str(method.pk)],
                                } for method in container_methods
                            ],
                        },
                        # remote_containers_step,
                    ],
                },
                {
                    "step": True,
                    "name": "Delete temporary files",
                    "parallel": True,
                    "children": [
                        {
                            "name": "ESSArch_Core.tasks.DeleteFiles",
                            "label": "Delete temporary container",
                            "queue": worker_queue,
                            "args": [temp_container_path]
                        },
                        {
                            "name": "ESSArch_Core.tasks.DeleteFiles",
                            "label": "Delete temporary AIP xml",
                            "queue": worker_queue,
                            "args": [temp_mets_path]
                        },
                        {
                            "name": "ESSArch_Core.tasks.DeleteFiles",
                            "label": "Delete temporary AIC xml",
                            "queue": worker_queue,
                            "if": temp_aic_mets_path,
                            "args": [temp_aic_mets_path]
                        },
                    ],
                },
                {
                    "name": "ESSArch_Core.ip.tasks.CreateReceipt",
                    "label": "Acknowledge API IP Migrated",
                    "queue": worker_queue,
                    "if": migration_receipt,
                    "params": {
                        "task_id": None,
                        "backend": "api_ip_migrated",
                        "template": None,
                        "destination": None,
                        "outcome": "success",
                        "short_message": "Migrated {{OBJID}}",
                        "message": "Migrated {{OBJID}}",
                        "storage_methods": [str(method.pk) for method in container_methods],
                    },
                },
            ]
        else:
            if is_cached_storage_object:
                workflow = [
                    {
                        "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                        "label": "Access AIP",
                        "queue": worker_queue,
                        "if": extracted and export_path,
                        "args": [str(self.pk)],
                        "params": {
                            "storage_object": str(storage_object.pk),
                            'dst': export_path_dst_extracted
                        },
                    },
                    {
                        "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                        "if": diff_check and extracted and export_path,
                        "label": "Redundancy check against content-mets",
                        "queue": worker_queue,
                        "args": [
                            export_path_dst_extracted,
                            export_path_dst_extracted_content_xml
                        ],
                    },
                    {
                        "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                        "label": "Access AIP",
                        "queue": worker_queue,
                        "if": tar,
                        "args": [str(self.pk)],
                        "params": {
                            "storage_object": str(storage_object.pk),
                            'dst': temp_object_path,
                        },
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.CreateContainer",
                        "label": "Create temporary container",
                        "queue": worker_queue,
                        "if": tar and export_path,
                        "args": [temp_object_path, export_path_dst_container],
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.GeneratePackageMets",
                        "label": "Create container mets",
                        "queue": worker_queue,
                        "if": tar and package_xml and export_path,
                        "args": [
                            export_path_dst_container,
                            export_path_dst_package_xml,
                        ]
                    },
                    {
                        "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                        "if": diff_check and tar and export_path,
                        "label": "Redundancy check against package-mets",
                        "queue": worker_queue,
                        "args": [
                            export_path_dst_container,
                            export_path_dst_package_xml,
                            [(Path(dst_object_identifier_value) / self.content_mets_path).as_posix(),
                             self.content_mets_path]
                        ],
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.GenerateAICMets",
                        "label": "Create container aic mets",
                        "queue": worker_queue,
                        "if": aic_xml and export_path,
                        "args": [export_path_dst_aic_xml]
                    },
                    {
                        "name": "ESSArch_Core.tasks.DeleteFiles",
                        "label": "Delete temporary object",
                        "queue": worker_queue,
                        "args": [temp_object_path]
                    },
                ]

            elif storage_object.container:
                # reading from long-term storage

                workflow = [
                    {
                        "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                        "label": "Access AIP",
                        "queue": worker_queue_1,
                        "args": [str(self.pk)],
                        "params": {
                            "storage_object": str(storage_object.pk),
                            'dst': temp_path
                        },
                    },
                    {
                        "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                        "if": diff_check and tar,
                        "label": "Redundancy check against package-mets",
                        "queue": worker_queue,
                        "args": [
                            temp_container_path,
                            temp_mets_path,
                            [(Path(dst_object_identifier_value) / self.content_mets_path).as_posix(),
                             self.content_mets_path],
                        ],
                    },
                    # {
                    #     "name": "ESSArch_Core.tasks.ExtractTAR",
                    #     "label": "Extract temporary container to cache",
                    #     "queue": worker_queue,
                    #     "if": storage_method.cached and cache_target is not None,
                    #     "allow_failure": True,
                    #     "args": [
                    #         temp_container_path,
                    #         cache_target,
                    #     ],
                    # },
                    {
                        "name": "ESSArch_Core.tasks.ExtractTAR",
                        "label": "Extract temporary container to export",
                        "queue": worker_queue,
                        "if": extracted and export_path,
                        "args": [
                            temp_container_path,
                            export_path_dst,
                        ],
                    },
                    # {
                    #     "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                    #     "if": diff_check and extracted,
                    #     "label": "Redundancy check against content-mets",
                    #     "queue": worker_queue,
                    #     "args": [
                    #         access_workarea_user_extracted,
                    #         access_workarea_user_extracted_content_xml
                    #     ],
                    # },
                    # {
                    #     "name": "ESSArch_Core.tasks.MoveDir",
                    #     "label": "Rename workspace to new generation",
                    #     "queue": worker_queue,
                    #     "if": extracted and new,
                    #     "args": [
                    #         access_workarea_user_extracted_src,
                    #         access_workarea_user_extracted,
                    #     ],
                    # },
                    {
                        "name": "ESSArch_Core.tasks.CopyFile",
                        "label": "Copy temporary container to export",
                        "queue": worker_queue,
                        "if": tar and export_path,
                        "args": [
                            temp_container_path,
                            export_path_dst_container,
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.CopyFile",
                        "label": "Copy temporary AIP xml to export",
                        "queue": worker_queue,
                        "if": package_xml and export_path,
                        "args": [
                            temp_mets_path,
                            export_path_dst_package_xml,
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.CopyFile",
                        "label": "Copy temporary AIC xml to export",
                        "queue": worker_queue,
                        "if": aic_xml and export_path,
                        "args": [
                            temp_aic_mets_path,
                            export_path_dst_aic_xml,
                        ],
                    },
                    {
                        "step": True,
                        "name": "Write to storage methods",
                        "parallel": True,
                        "children": [
                            {
                                "step": True,
                                "name": "Write non-containers",
                                "if": non_container_methods.exists(),
                                "children": [
                                    {
                                        "name": "ESSArch_Core.tasks.ExtractTAR",
                                        "label": "Extract temporary container to temporary path",
                                        "queue": worker_queue,
                                        "args": [
                                            temp_container_path,
                                            temp_path,
                                        ],
                                    },
                                    {
                                        "step": True,
                                        "parallel": True,
                                        "name": "Write non-containers to storage methods",
                                        "if": non_container_methods.exists(),
                                        "children": [
                                            {
                                                "name": "ESSArch_Core.ip.tasks.PreserveInformationPackage",
                                                "label": "Write to storage method ({})".format(method.name),
                                                "args": [str(method.pk), temp_path],
                                            } for method in non_container_methods
                                        ]
                                    },
                                    {
                                        "name": "ESSArch_Core.tasks.DeleteFiles",
                                        "label": "Delete temporary object",
                                        "queue": worker_queue,
                                        "args": [temp_object_path]
                                    },
                                ],
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
                                                "label": "Write to storage method ({})".format(method.name),
                                                "queue": worker_queue,
                                                "args": [str(method.pk), temp_path],
                                            } for method in container_methods
                                        ],
                                    },
                                    # remote_containers_step,
                                ],
                            },
                        ],
                    },
                    {
                        "step": True,
                        "name": "Delete temporary files",
                        "parallel": True,
                        "children": [
                            {
                                "name": "ESSArch_Core.tasks.DeleteFiles",
                                "label": "Delete temporary container",
                                "queue": worker_queue,
                                "args": [temp_container_path]
                            },
                            {
                                "name": "ESSArch_Core.tasks.DeleteFiles",
                                "label": "Delete temporary AIP xml",
                                "queue": worker_queue,
                                "args": [temp_mets_path]
                            },
                            {
                                "name": "ESSArch_Core.tasks.DeleteFiles",
                                "label": "Delete temporary AIC xml",
                                "queue": worker_queue,
                                "if": temp_aic_mets_path,
                                "args": [temp_aic_mets_path]
                            },
                        ],
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.CreateReceipt",
                        "label": "Acknowledge API IP Migrated",
                        "queue": worker_queue,
                        "if": migration_receipt,
                        "params": {
                            "task_id": None,
                            "backend": "api_ip_migrated",
                            "template": None,
                            "destination": None,
                            "outcome": "success",
                            "short_message": "Migrated {{OBJID}}",
                            "message": "Migrated {{OBJID}}",
                            "storage_methods": ([str(method.pk) for method in container_methods] +
                                                [str(method.pk) for method in non_container_methods]),
                        },
                    },
                ]
            else:
                # reading from non long-term storage

                workflow = [
                    {
                        "name": "ESSArch_Core.workflow.tasks.AccessAIP",
                        "label": "Access AIP",
                        "queue": worker_queue,
                        "if": tar,
                        "args": [str(self.pk)],
                        "params": {
                            "storage_object": str(storage_object.pk),
                            'dst': temp_object_path,
                        },
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.CreateContainer",
                        "label": "Create temporary container",
                        "queue": worker_queue,
                        "if": tar,
                        "args": [temp_object_path, temp_container_path],
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.GeneratePackageMets",
                        "label": "Create container mets",
                        "queue": worker_queue,
                        "if": tar and package_xml,
                        "args": [
                            temp_container_path,
                            temp_mets_path,
                        ]
                    },
                    {
                        "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                        "if": diff_check and tar,
                        "label": "Redundancy check against package-mets",
                        "queue": worker_queue,
                        "args": [
                            temp_container_path,
                            temp_mets_path,
                            [(Path(dst_object_identifier_value) / self.content_mets_path).as_posix(),
                             self.content_mets_path]
                        ],
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.GenerateAICMets",
                        "label": "Create container aic mets",
                        "queue": worker_queue,
                        "if": aic_xml,
                        "args": [temp_aic_mets_path]
                    },
                    {
                        "name": "ESSArch_Core.tasks.CopyFile",
                        "label": "Copy temporary container to export",
                        "queue": worker_queue,
                        "if": tar and export_path,
                        "args": [
                            temp_container_path,
                            export_path_dst_container,
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.CopyFile",
                        "label": "Copy temporary AIP xml to export",
                        "queue": worker_queue,
                        "if": package_xml and export_path,
                        "args": [
                            temp_mets_path,
                            export_path_dst_package_xml,
                        ],
                    },
                    {
                        "name": "ESSArch_Core.tasks.CopyFile",
                        "label": "Copy temporary AIC xml to export",
                        "queue": worker_queue,
                        "if": aic_xml and export_path,
                        "args": [
                            temp_aic_mets_path,
                            export_path_dst_aic_xml,
                        ],
                    },
                    {
                        "step": True,
                        "name": "Write to storage methods",
                        "parallel": True,
                        "children": [
                            {
                                "step": True,
                                "name": "Write non-containers",
                                "if": non_container_methods.exists(),
                                "children": [
                                    {
                                        "step": True,
                                        "parallel": True,
                                        "name": "Write non-containers to storage methods",
                                        "if": non_container_methods.exists(),
                                        "children": [
                                            {
                                                "name": "ESSArch_Core.ip.tasks.PreserveInformationPackage",
                                                "label": "Write to storage method ({})".format(method.name),
                                                "args": [str(method.pk), temp_path],
                                            } for method in non_container_methods
                                        ]
                                    },
                                    {
                                        "name": "ESSArch_Core.tasks.DeleteFiles",
                                        "label": "Delete temporary object",
                                        "queue": worker_queue,
                                        "args": [temp_object_path]
                                    },
                                ],
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
                                                "label": "Write to storage method ({})".format(method.name),
                                                "queue": worker_queue,
                                                "args": [str(method.pk), temp_path],
                                            } for method in container_methods
                                        ],
                                    },
                                    # remote_containers_step,
                                ],
                            },
                        ],
                    },
                    {
                        "step": True,
                        "name": "Delete temporary files",
                        "parallel": True,
                        "children": [
                            {
                                "name": "ESSArch_Core.tasks.DeleteFiles",
                                "label": "Delete temporary container",
                                "queue": worker_queue,
                                "args": [temp_container_path]
                            },
                            {
                                "name": "ESSArch_Core.tasks.DeleteFiles",
                                "label": "Delete temporary AIP xml",
                                "queue": worker_queue,
                                "args": [temp_mets_path]
                            },
                            {
                                "name": "ESSArch_Core.tasks.DeleteFiles",
                                "label": "Delete temporary AIC xml",
                                "queue": worker_queue,
                                "if": temp_aic_mets_path,
                                "args": [temp_aic_mets_path]
                            },
                        ],
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.CreateReceipt",
                        "label": "Acknowledge API IP Migrated",
                        "queue": worker_queue,
                        "if": migration_receipt,
                        "params": {
                            "task_id": None,
                            "backend": "api_ip_migrated",
                            "template": None,
                            "destination": None,
                            "outcome": "success",
                            "short_message": "Migrated {{OBJID}}",
                            "message": "Migrated {{OBJID}}",
                            "storage_methods": ([str(method.pk) for method in container_methods] +
                                                [str(method.pk) for method in non_container_methods]),
                        },
                    },
                ]

        # create workflow step
        ip_migrate_workflow_step = create_workflow(
            workflow, self,
            name='Migrate Information Package',
            label='Migrate Information Package',
            responsible=responsible,
            part_root=True,
            top_root_step=top_root_step,
        )

        return ip_migrate_workflow_step

    def write_to_search_index(self, task):
        logger = logging.getLogger('essarch.ip')
        srcdir = self.object_path
        ct_profile = self.get_profile('content_type')
        indexed_files = []

        profile_type = self.get_package_type_display().lower()
        index_cits = self.get_profile_data(profile_type).get('index_cits', True)
        if ct_profile is not None and (index_cits is True or index_cits == 'True'):
            cts = self.get_content_type_file()
            if cts is not None:
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
                    err = "Content type specification file not found"
                    logger.error('{err}: {path}'.format(err=err, path=cts))
                    raise OSError(errno.ENOENT, err, cts)
            else:
                logger.info('No content type specification specified in profile')
                try:
                    ct_importer_name = ct_profile.specification['name']
                except KeyError:
                    logger.exception('No content type importer specified in profile')
                    raise
                ct_importer = get_importer(ct_importer_name)(task)
                indexed_files = ct_importer.import_content(cts, ip=self)

        index_files = self.get_profile_data(profile_type).get('index_files', True)
        index_files_content = self.get_profile_data(profile_type).get('index_files_content', True)
        if index_files is True or index_files == 'True':
            group = None
            try:
                group = self.get_organization()
            except ObjectDoesNotExist:
                group = None
            if group is not None:
                group = group.group

            for root, dirs, files in walk(srcdir):
                for d in dirs:
                    src = os.path.join(root, d)
                    index_path(self, src, group=group, index_file_content=index_files_content)

                for f in files:
                    src = os.path.join(root, f)
                    try:
                        # check if file has already been indexed
                        indexed_files.remove(src)
                    except ValueError:
                        # file has not been indexed, index it
                        index_path(self, src, group=group, index_file_content=index_files_content)

        InformationPackageDocument.from_obj(self).save()

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
        logger = logging.getLogger('essarch.ip')
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

    def get_temp_object_path(self, temp_path=None):
        temp_dir = temp_path if temp_path else cmPath.objects.get(entity='temp').value
        return (Path(temp_dir) / self.object_identifier_value).as_posix()

    def get_temp_container_path(self, temp_path=None):
        temp_dir = temp_path if temp_path else cmPath.objects.get(entity='temp').value
        container_format = self.get_container_format()
        return (Path(temp_dir) / f'{self.object_identifier_value}.{container_format}').as_posix()

    def get_temp_container_xml_path(self, temp_path=None):
        temp_dir = temp_path if temp_path else cmPath.objects.get(entity='temp').value
        if not self.package_mets_path:
            return ''
        else:
            return (Path(temp_dir) / self.package_mets_path.split('/')[-1]).as_posix()

    def get_temp_container_aic_xml_path(self, temp_path=None):
        temp_dir = temp_path if temp_path else cmPath.objects.get(entity='temp').value
        return (Path(temp_dir) / f'{self.aic.object_identifier_value}.xml').as_posix()

    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logging.getLogger('essarch.ip'), logging.DEBUG))
    def update_remote_ip(self, host, session):
        logger = logging.getLogger('essarch.ip')
        from ESSArch_Core.ip.serializers import (
            InformationPackageFromMasterSerializer,
        )

        remote_ip = urljoin(host, reverse('informationpackage-add-from-master'))
        data = InformationPackageFromMasterSerializer(instance=self).data
        response = session.post(remote_ip, json=data, timeout=10)
        try:
            response.raise_for_status()
        except RequestException:
            logger.exception("Problem to add IP: {} to remote server. Response: {}".format(self, response.text))
            raise

    @retry(retry=retry_if_exception_type(StorageMediumFull), reraise=True, stop=stop_after_attempt(2),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logging.getLogger('essarch.ip'), logging.DEBUG))
    def preserve(self, src: list, storage_target, container: bool, task):
        logger = logging.getLogger('essarch.ip')
        qs = StorageMedium.objects.filter(
            storage_target__methods__containers=container,
        ).writeable().natural_sort()

        write_size = 0
        for s in src:
            write_size += get_tree_size_and_count(s)[0]
        fsize_mb = write_size / MB

        if storage_target.remote_server:
            session = requests.Session()
            session.verify = settings.REQUESTS_VERIFY
            server_list = storage_target.remote_server.split(',')
            if len(server_list) == 2:
                host, token = server_list
                session.headers['Authorization'] = 'Token %s' % token
            else:
                host, user, passw = server_list
                token = None
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

                if task.status == celery_states.PENDING:
                    task.run_remote_copy(session, host)
                elif task.status != celery_states.SUCCESS:
                    logger.debug('task.status: {}'.format(task.status))
                    task.retry_remote_copy(session, host)
                    task.status = celery_states.PENDING

            time_start = time.time()
            while task.status not in celery_states.READY_STATES:
                session = requests.Session()
                session.verify = settings.REQUESTS_VERIFY
                if token:
                    session.headers['Authorization'] = 'Token %s' % token
                else:
                    session.auth = (user, passw)
                r = task.get_remote_copy(session, host)

                remote_data = r.json()
                task.status = remote_data['status']
                task.progress = remote_data['progress']
                task.result = remote_data['result']
                task.traceback = remote_data['traceback']
                task.exception = remote_data['exception']
                task.save()

                sleep(5)
            time_end = time.time()
            time_elapsed = time_end - time_start

            if task.status in celery_states.EXCEPTION_STATES:
                task.reraise()
            storage_object = StorageObject.create_from_remote_copy(host, session, task.result.split(',')[0])
        else:
            storage_medium, created = storage_target.get_or_create_storage_medium(qs=qs)

            new_size = storage_medium.used_capacity + write_size
            if new_size > storage_target.max_capacity > 0:
                storage_medium.mark_as_full()
                raise StorageMediumFull(
                    'Maximum capacity limit reached for storage medium {} "{}"'.format(
                        storage_medium.medium_id, str(storage_medium.pk)))

            storage_backend = storage_target.get_storage_backend()
            storage_medium.prepare_for_write(io_lock_key=src)
            if storage_medium.status == 100:
                raise StorageMediumError(
                    'Storage medium {} "{}" is failed'.format(storage_medium.medium_id, str(storage_medium.pk)))
            if storage_backend.type == 300 and storage_medium.tape_drive is not None:
                if storage_medium.tape_drive.status == 100:
                    raise StorageMediumError(
                        'Storage medium {} "{}" is failed'.format(storage_medium.medium_id, str(storage_medium.pk)))
            elif storage_backend.type == 300 and storage_medium.tape_drive is None:
                raise StorageMediumError(
                    'Storage medium {} "{}" is not online in drive'.format(storage_medium.medium_id,
                                                                           str(storage_medium.pk)))
            time_start = time.time()
            storage_object = storage_backend.write(src, self, container, storage_medium)
            StorageMedium.objects.filter(pk=storage_medium.pk).update(
                used_capacity=F('used_capacity') + write_size,
                last_changed_local=timezone.now(),
            )
            time_end = time.time()
            time_elapsed = time_end - time_start

        if storage_target.remote_server:
            mb_per_sec = float(re.findall("([0-9]+[.]+[0-9]+)", task.result.split(',')[2])[0])
        else:
            try:
                mb_per_sec = fsize_mb / time_elapsed
            except ZeroDivisionError:
                mb_per_sec = fsize_mb
        medium_id = storage_object.storage_medium.medium_id

        return (str(storage_object.pk), medium_id, write_size, mb_per_sec, time_elapsed)

    def access(self, storage_object, task, dst=None, local=True):
        logger = logging.getLogger('essarch.ip')
        logger.debug('Accessing information package {} from storage object {}'.format(
            self.object_identifier_value, str(storage_object.pk),
        ))

        storage_object.read(dst, task, local=local)

    def open_file(self, path='', *args, **kwargs):
        logger = logging.getLogger('essarch.ip')
        if self.archived:
            storage_obj = self.storage.readable().fastest().first()
            if storage_obj is None:
                raise ValueError("No readable storage configured for IP")
            logger.debug(f'Opening file {path} from storage object {storage_obj}')
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

    def delete_temp_files(self):
        paths = [
            os.path.join(cmPath.objects.get(entity='temp').value, 'file_upload', str(self.pk)),
            os.path.join(cmPath.objects.get(entity='temp').value, str(self.pk)),
            os.path.join(cmPath.objects.get(entity='temp').value, str(self.object_identifier_value)),
        ]

        for path in paths:
            delete_path(path)

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
            workarea.delete_temp_files()
            workarea.delete_files()
            workarea.delete()

    class Meta:
        ordering = ["generation", "-create_date"]
        verbose_name = _('information package')
        verbose_name_plural = _('information packages')
        unique_together = (
            ('aic', 'generation'),
        )
        indexes = [
            models.Index(fields=['state', 'package_type', 'active', 'archived', 'generation', 'aic_id']),
        ]
        permissions = (
            ('can_upload', 'Can upload files to IP'),
            ('set_uploaded', 'Can set IP as uploaded'),
            ('prepare_sip', 'Can prepare SIP'),
            ('create_sip', 'Can create SIP'),
            ('submit_sip', 'Can submit SIP'),
            ('transfer_sip', 'Can transfer SIP'),
            ('change_sa', 'Can change SA connected to IP'),
            ('change_organization', 'Can change organization for IP'),
            ('lock_sa', 'Can lock SA to IP'),
            ('unlock_profile', 'Can unlock profile connected to IP'),
            ('can_receive_remote_files', 'Can receive remote files'),
            ('receive', 'Can receive IP'),
            ('preserve', 'Can preserve IP'),
            ('prepare_dip', 'Can prepare DIP'),
            ('preserve_dip', 'Can preserve DIP'),
            ('get_from_storage', 'Can get extracted IP from storage'),
            ('get_tar_from_storage', 'Can get packaged IP from storage'),
            ('get_from_storage_as_new', 'Can get IP "as new" from storage'),
            ('create_as_new', 'Can create IP as new generation'),
            ('add_to_ingest_workarea', 'Can add IP to ingest workarea'),
            ('add_to_ingest_workarea_as_tar', 'Can add IP as tar to ingest workarea'),
            ('add_to_ingest_workarea_as_new', 'Can add IP as new generation to ingest workarea'),
            ('diff-check', 'Can diff-check IP'),
            ('query', 'Can query IP'),
            ('prepare_ip', 'Can prepare IP'),
            ('delete_first_generation', 'Can delete first generation of IP'),
            ('delete_last_generation', 'Can delete last generation of IP'),
            ('delete_archived', 'Can delete archived IP'),
            ('delete_reception', 'Can delete reception IP'),
            ('see_all_in_workspaces', 'Can see all IPs workspaces'),
            ('see_other_user_ip_files', 'Can see files in other users IPs'),
        )

    def __str__(self):
        return '{} ({})'.format(self.label, self.object_identifier_value)

    def get_value_array(self):
        # make an associative array of all fields  mapping the field
        # name to the current value of the field
        return {
            field.name: field.value_to_string(self)
            for field in InformationPackage._meta.fields
        }


class InformationPackageUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(InformationPackage, on_delete=models.CASCADE)


class InformationPackageGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(InformationPackage, on_delete=models.CASCADE)


class InformationPackageGroupObjects(GroupObjectsBase):
    content_object = models.ForeignKey(InformationPackage, on_delete=models.CASCADE)


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

    last_changed_local = models.DateTimeField(auto_now=True)
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
        parser = etree.XMLParser(resolve_entities=False)
        root = etree.parse(xmlfile, parser=parser).getroot()
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
    eventIdentifierValue = models.UUIDField(default=uuid.uuid4, unique=True)
    eventType = models.ForeignKey(
        'configuration.EventType',
        on_delete=models.CASCADE
    )
    eventDateTime = models.DateTimeField(default=timezone.now, db_index=True)
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
    linkingObjectIdentifierValue = models.CharField(max_length=255, blank=True, db_index=True)
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
    successfully_validated = models.JSONField(default=None, null=True)

    @property
    def path(self):
        area_dir = cmPath.objects.get(entity=self.get_type_display() + '_workarea').value
        return (Path(area_dir) / self.user.username / self.ip.object_identifier_value).as_posix()

    @property
    def package_xml_path(self):
        area_dir = cmPath.objects.get(entity=self.get_type_display() + '_workarea').value
        return (Path(area_dir) / self.user.username / self.ip.object_identifier_value /
                self.ip.package_mets_path.split('/')[-1]).as_posix()

    @property
    def aic_xml_path(self):
        area_dir = cmPath.objects.get(entity=self.get_type_display() + '_workarea').value
        return (Path(area_dir) / self.user.username / self.ip.object_identifier_value /
                f'{self.ip.aic.object_identifier_value}.xml').as_posix()

    def get_path(self):
        return self.path

    def delete_temp_files(self):
        temp_path = (Path(cmPath.objects.get(entity='temp').value) / 'file_upload' / str(self.pk)).as_posix()
        delete_path(temp_path)

    def delete_files(self):
        path = self.get_path()
        self.delete_temp_files()
        delete_path(path)

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
        root = cmPath.objects.get(entity='orders').value
        return (Path(root) / str(self.pk)).as_posix()

    class Meta:
        ordering = ["label"]
        permissions = (
            ('prepare_order', 'Can prepare order'),
        )
