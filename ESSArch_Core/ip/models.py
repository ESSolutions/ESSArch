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

import errno
import io
import logging
import math
import os
import shutil
import tarfile
import uuid
import zipfile
from copy import deepcopy
from datetime import datetime

import jsonfield
from celery import states as celery_states
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import models, transaction
from django.db.models import Count, Max, Min
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from lxml import etree
from groups_manager.utils import get_permission_name
from guardian.shortcuts import assign_perm
from rest_framework import exceptions
from rest_framework.response import Response

from ESSArch_Core.auth.models import GroupGenericObjects, Member
from ESSArch_Core.auth.util import get_objects_for_user
from ESSArch_Core.configuration.models import ArchivePolicy, Path
from ESSArch_Core.essxml.Generator.xmlGenerator import parseContent
from ESSArch_Core.fixity.format import FormatIdentifier
from ESSArch_Core.profiles.models import ProfileIP, ProfileIPData, ProfileSA
from ESSArch_Core.profiles.models import SubmissionAgreement as SA
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.search.importers import get_backend as get_importer
from ESSArch_Core.util import (
    find_destination,
    generate_file_response,
    get_files_and_dirs,
    get_tree_size_and_count,
    in_directory,
    normalize_path,
    timestamp_to_datetime,
)

logger = logging.getLogger('essarch.ip')

MESSAGE_DIGEST_ALGORITHM_CHOICES = (
    (ArchivePolicy.MD5, 'MD5'),
    (ArchivePolicy.SHA1, 'SHA-1'),
    (ArchivePolicy.SHA224, 'SHA-224'),
    (ArchivePolicy.SHA256, 'SHA-256'),
    (ArchivePolicy.SHA384, 'SHA-384'),
    (ArchivePolicy.SHA512, 'SHA-512'),
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


class InformationPackageManager(models.Manager):
    def for_user(self, user, perms, include_no_auth_objs=True):
        """
        Returns information packages for which a given ``users`` groups in the
        ``users`` current organization has all permissions in ``perms``

        :param user: ``User`` instance for which information packages would be
        returned
        :param perms: single permission string, or sequence of permission
        strings which should be checked
        """

        return get_objects_for_user(user, self.model, perms, include_no_auth_objs)

    def visible_to_user(self, user):
        return self.for_user(user, 'view_informationpackage', include_no_auth_objs=False)


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

    package_type = models.IntegerField(_('package type'), null=True, choices=PACKAGE_TYPE_CHOICES)
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
        'configuration.ArchivePolicy',
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

    def get_lock_key(self):
        return 'lock_ip_{}'.format(str(self.pk))

    def is_locked(self):
        return self.get_lock_key() in cache

    def get_lock(self):
        return cache.lock(self.get_lock_key())

    def get_permissions(self, user, checker=None):
        return user.get_all_permissions(self)

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

    def change_organization(self, organization):
        if organization.group_type.codename != 'organization':
            raise ValueError('{} is not an organization'.format(organization))
        ctype = ContentType.objects.get_for_model(self)
        GroupGenericObjects.objects.update_or_create(object_id=self.pk, content_type=ctype,
                                                     defaults={'group': organization})

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
            logger.error(msg)
            raise ValueError(msg)

        try:
            return ct_profile.specification['name']
        except KeyError:
            logger.exception('No content type importer specified in {profile}'.format(profile=ct_profile.name))
            raise

    def get_content_type_file(self):
        ctsdir, ctsfile = find_destination('content_type_specification', self.get_structure())
        if ctsdir is None:
            return None
        return parseContent(os.path.join(ctsdir, ctsfile), fill_specification_data(ip=self))

    def get_archive_tag(self):
        if self.tag is not None:
            return self.tag

        try:
            ct_importer_name = self.get_content_type_importer_name()
            ct_importer = get_importer(ct_importer_name)()
            cts_file = self.open_file(self.get_content_type_file())
            tag = ct_importer.get_archive(cts_file)

            if tag is None:
                return self.tag

            return tag
        except ValueError:
            return None

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
        except BaseException:
            return 'tar'

    def get_checksum_algorithm(self):
        try:
            if self.profile_type == InformationPackage.SIP:
                name = self.get_profile_data('transfer_project').get(
                    'checksum_algorithm', 'SHA-256'
                )
            else:
                name = self.policy.get_checksum_algorithm_display().upper()
        except BaseException:
            name = 'SHA-256'

        return name

    def get_email_recipient(self):
        try:
            return self.get_profile_data('transfer_project').get(
                'preservation_organization_receiver_email'
            )
        except BaseException:
            return None

    def get_structure(self):
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
        premis_dir, premis_name = find_destination("preservation_description_file", self.get_structure())
        if premis_dir is not None:
            path = os.path.join(premis_dir, premis_name)
            path = parseContent(path, fill_specification_data(ip=self))
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

            if 'information_packages' in self.aic._prefetched_objects_cache:
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

                if ip_step_state == celery_states.STARTED:
                    state = ip_step_state
                if (ip_step_state == celery_states.PENDING and
                        state != celery_states.STARTED):
                    state = ip_step_state
                if ip_step_state == celery_states.FAILURE:
                    return ip_step_state

            return state

        tasks = self.processtask_set.filter(hidden=False)
        state = celery_states.SUCCESS
        for task in tasks:
            task_status = task.status

            if task_status == celery_states.STARTED:
                state = task_status
            if (task_status == celery_states.PENDING and
                    state != celery_states.STARTED):
                state = task_status
            if task_status == celery_states.FAILURE:
                return task_status

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

                progress += math.ceil(ip_profiles_locked.count() * ((100 - progress) / sa_profiles.count()))

            except ZeroDivisionError:
                pass

            return progress

        steps = self.steps.all()
        if steps.exists():
            progress = sum([s.progress for s in steps])
            return progress / steps.count()

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
            raise exceptions.ValidationError(u'Illegal path: {s}'.format(path))

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
        except (IOError, OSError) as e:
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
                    u'{}.xml'.format(self.object_identifier_value)
                )
            if os.path.join(os.path.dirname(self.object_path), path) == xmlfile:
                return open(xmlfile, *args)

            try:
                with tarfile.open(self.object_path) as tar:
                    try:
                        f = tar.extractfile(path)
                    except KeyError:
                        full_path = normalize_path(os.path.join(self.object_identifier_value, path))
                        f = tar.extractfile(full_path)
                    return io.BytesIO(f.read())
            except tarfile.ReadError:
                logger.debug('Invalid tar file, trying zipfile instead')
                try:
                    with zipfile.ZipFile(self.object_path) as zipf:
                        try:
                            f = zipf.open(path)
                        except KeyError:
                            full_path = normalize_path(os.path.join(self.object_identifier_value, path))
                            f = zipf.open(full_path)
                        return io.BytesIO(f.read())
                except zipfile.BadZipfile:
                    logger.debug('Invalid zip file')
            except KeyError:
                raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), os.path.join(self.object_path, path))

        return open(os.path.join(self.object_path, path), *args, **kwargs)

    def delete_files(self):
        path = self.get_path()

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
    def from_premis_element(self, el, save=True):
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
        if save:
            event.save()
        return event

    def from_premis_file(self, xmlfile, save=True):
        root = etree.parse(xmlfile).getroot()
        return [self.from_premis_element(el, save) for el in root.xpath("./*[local-name()='event']")]


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
    eventOutcomeDetailNote = models.CharField(max_length=1024)  # Result or traceback from IP
    linkingAgentIdentifierValue = models.CharField(max_length=255, blank=True)
    linkingAgentRole = models.CharField(max_length=255, blank=True)
    linkingObjectIdentifierValue = models.CharField(max_length=255, blank=True)

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
    successfully_validated = jsonfield.JSONField(default=None, null=True)

    @property
    def path(self):
        area_dir = Path.objects.cached('entity', self.get_type_display() + '_workarea', 'value')
        return os.path.join(area_dir, self.user.username, self.ip.object_identifier_value)

    def get_path(self):
        return self.path

    class Meta:
        unique_together = ('user', 'ip', 'type')
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
