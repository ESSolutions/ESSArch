import errno
import logging
import os
import pickle
import shutil
import tarfile
import uuid
from datetime import timedelta
from time import sleep
from urllib.parse import urljoin

import requests
from celery import states as celery_states
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models, transaction
from django.db.models import (
    Case,
    Exists,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Cast
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from picklefield.fields import PickledObjectField
from requests import RequestException
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from ESSArch_Core.configuration.models import Parameter, Path, StoragePolicy
from ESSArch_Core.db.utils import natural_sort
from ESSArch_Core.fixity.validation.backends.checksum import ChecksumValidator
from ESSArch_Core.storage.backends import get_backend
from ESSArch_Core.storage.copy import copy_file
from ESSArch_Core.storage.tape import read_tape, set_tape_file_number
from ESSArch_Core.util import delete_path

DRIVE_LOCK_PREFIX = 'lock_drive_'
DISK = 200
TAPE = 300
CAS = 400

IOReqType_CHOICES = (
    (10, 'Write to tape'),
    (15, 'Write to disk'),
    (20, 'Read from tape'),
    (25, 'Read from disk'),
    (41, 'Write to HDFS'),
    (42, 'Read from HDFS'),
    (43, 'Write to HDFS-REST'),
    (44, 'Read from HDFS-REST'),
)

req_status_CHOICES = (
    (-1, 'Inactive'),
    (0, 'Pending'),
    (2, 'Initiate'),
    (5, 'Progress'),
    (20, 'Success'),
    (100, 'FAIL'),
)

remote_status_CHOICES = (
    (0, 'Pending'),
    (2, 'Initiate'),
    (5, 'Transfer'),
    (20, 'Success'),
    (100, 'FAIL'),
)

robot_req_type_CHOICES = (
    (10, 'mount'),
    (20, 'unmount'),
    (30, 'unmount_force'),
)

medium_type_CHOICES = (
    (200, 'DISK'),
    (301, 'IBM-LTO1'),
    (302, 'IBM-LTO2'),
    (303, 'IBM-LTO3'),
    (304, 'IBM-LTO4'),
    (305, 'IBM-LTO5'),
    (306, 'IBM-LTO6'),
    (307, 'IBM-LTO7'),
    (308, 'IBM-LTO8'),
    (309, 'IBM-LTO9'),
    (325, 'HP-LTO5'),
    (326, 'HP-LTO6'),
    (327, 'HP-LTO7'),
    (328, 'HP-LTO8'),
    (329, 'HP-LTO9'),
    (401, 'HDFS'),
    (402, 'HDFS-REST'),
)
medium_type_CHOICES_DICT = {v: k for k, v in medium_type_CHOICES}

storage_type_CHOICES = (
    (DISK, 'DISK'),
    (TAPE, 'TAPE'),
    (CAS, 'CAS'),
)
storage_type_CHOICES_DICT = {v: k for k, v in storage_type_CHOICES}

medium_format_CHOICES = (
    (103, '103 (AIC support)'),
    (102, '102 (Media label)'),
    (101, '101 (Old read only)'),
    (100, '100 (Old read only)'),
)
medium_format_CHOICES_DICT = {v: k for k, v in medium_format_CHOICES}

medium_status_CHOICES = (
    (0, 'Inactive'),
    (20, 'Write'),
    (30, 'Full'),
    (100, 'FAIL'),
)
medium_status_CHOICES_DICT = {v: k for k, v in medium_status_CHOICES}

medium_location_status_CHOICES = (
    (10, 'Delivered'),
    (20, 'Received'),
    (30, 'Placed'),
    (40, 'Collected'),
    (50, 'Robot'),
)
medium_location_status_CHOICES_DICT = {v: k for k, v in medium_location_status_CHOICES}

medium_block_size_CHOICES = (
    (128, '64K'),
    (250, '125K'),
    (256, '128K'),
    (512, '256K'),
    (1024, '512K'),
    (2048, '1024K'),
)
medium_block_size_CHOICES_DICT = {v: k for k, v in medium_block_size_CHOICES}

STORAGE_TARGET_STATUS_DISABLED = 0
STORAGE_TARGET_STATUS_ENABLED = 1
STORAGE_TARGET_STATUS_READ_ONLY = 2
STORAGE_TARGET_STATUS_MIGRATE = 3

storage_target_status_CHOICES = (
    (STORAGE_TARGET_STATUS_DISABLED, 'Disabled'),
    (STORAGE_TARGET_STATUS_ENABLED, 'Enabled'),
    (STORAGE_TARGET_STATUS_READ_ONLY, 'ReadOnly'),
    (STORAGE_TARGET_STATUS_MIGRATE, 'Migrate'),
)
storage_target_status_CHOICES_DICT = {v: k for k, v in storage_target_status_CHOICES}

min_chunk_size_CHOICES = (
    (0, 'Disabled'),
    (1048576, '1 MByte'),
    (1073741824, '1 GByte'),
    (53687091201, '5 GByte'),
    (10737418240, '10 GByte'),
    (107374182400, '100 GByte'),
    (214748364800, '200 GByte'),
    (322122547200, '300 GByte'),
    (429496729600, '400 GByte'),
    (536870912000, '500 GByte'),
)
min_chunk_size_CHOICES_DICT = {v: k for k, v in min_chunk_size_CHOICES}


def get_backend_from_storage_type(type):
    return {
        DISK: 'disk',
        TAPE: 'tape',
        CAS: 's3',
    }[type]


def get_storage_type_from_medium_type(medium_type):
    if DISK <= medium_type < TAPE:
        return DISK

    if TAPE <= medium_type < CAS:
        return TAPE

    return CAS


class StorageMethodQueryset(models.QuerySet):
    def archival_storage(self):
        return self.filter(containers=False)

    def secure_storage(self):
        return self.filter(containers=True)

    def filter_has_target_with_status(self, status: int, value: bool):
        annotation_key = 'has_target_with_status_{}'.format(status)
        qs = self.annotate(
            **{
                annotation_key: Exists(
                    StorageMethodTargetRelation.objects.filter(
                        storage_method=OuterRef('pk'),
                        status=status,
                    )
                )
            }
        ).filter(**{annotation_key: value})
        return self.filter(pk__in=qs)

    def fastest(self):
        container = Case(
            When(containers=False, then=Value(1)),
            When(containers=True, then=Value(2)),
            output_field=IntegerField(),
        )
        remote = Case(
            When(remote=True, then=Value(1)),
            When(remote=False, then=Value(2)),
            output_field=IntegerField(),
        )
        storage_type = Case(
            When(type=DISK, then=Value(1)),
            When(type=TAPE, then=Value(2)),
            output_field=IntegerField(),
        )
        return self.annotate(
            container_order=container,
            remote_order=remote,
            storage_type=storage_type
        ).order_by('remote_order', 'container_order', 'storage_type')


class StorageMethod(models.Model):
    """Disk, tape or CAS"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('Name', max_length=255, blank=True)
    enabled = models.BooleanField('Enabled', default=True)
    type = models.IntegerField('Type', choices=storage_type_CHOICES, default=200)
    remote = models.BooleanField('remote', default=False)
    containers = models.BooleanField('Long-term', default=False)
    targets = models.ManyToManyField('StorageTarget', through='StorageMethodTargetRelation', related_name='methods')
    cached = models.BooleanField('Cached', default=True)

    objects = StorageMethodQueryset.as_manager()

    @property
    def enabled_target(self):
        return StorageTarget.objects.get(
            status=True,
            storage_method_target_relations__storage_method=self,
            storage_method_target_relations__status=STORAGE_TARGET_STATUS_ENABLED,
        )

    class Meta:
        ordering = ['name']

    def __str__(self):
        if len(self.name):
            return self.name

        return str(self.id)


class StorageMethodTargetRelation(models.Model):
    """Relation between StorageMethod and StorageTarget"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('Name', max_length=255, blank=True)
    status = models.IntegerField(
        'Storage target status',
        choices=storage_target_status_CHOICES,
        default=STORAGE_TARGET_STATUS_DISABLED,
        db_index=True,
    )
    storage_target = models.ForeignKey(
        'StorageTarget',
        on_delete=models.CASCADE,
        related_name='storage_method_target_relations',
    )
    storage_method = models.ForeignKey(
        'StorageMethod',
        on_delete=models.CASCADE,
        related_name='storage_method_target_relations',
    )

    class Meta:
        verbose_name = 'Storage Method/Target Relation'
        ordering = ['name']
        unique_together = ('storage_method', 'storage_target')

    def save(self, *args, **kwargs):
        if self.status == STORAGE_TARGET_STATUS_ENABLED:
            if StorageMethodTargetRelation.objects.filter(
                storage_method=self.storage_method,
                status=STORAGE_TARGET_STATUS_ENABLED,
            ).exists():
                raise ValidationError(_('Only 1 target can be enabled for a storage method at a time'),)
        return super().save(*args, **kwargs)

    def __str__(self):
        if len(self.name):
            return self.name

        return str(self.id)


class StorageTargetQueryset(models.QuerySet):
    def archival_storage(self):
        return self.filter(methods__containers=False)

    def secure_storage(self):
        return self.filter(methods__containers=True)

    def fastest(self):
        container = Case(
            When(methods__containers=False, then=Value(1)),
            When(methods__containers=True, then=Value(2)),
            output_field=IntegerField(),
        )
        remote = Case(
            When(remote_server__isnull=True, then=Value(1)),
            When(remote_server__isnull=False, then=Value(2)),
            output_field=IntegerField(),
        )
        storage_type = Case(
            When(methods__type=DISK, then=Value(1)),
            When(methods__type=TAPE, then=Value(2)),
            output_field=IntegerField(),
        )
        return self.annotate(
            container_order=container,
            remote=remote,
            storage_type=storage_type
        ).order_by('remote', 'container_order', 'storage_type')


class StorageTarget(models.Model):
    """A series of tapes or a single disk"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('Name', max_length=255, unique=True)
    status = models.BooleanField('Storage target status', default=True)
    type = models.IntegerField('Type', choices=medium_type_CHOICES, default=200)
    default_block_size = models.IntegerField(
        'Default block size (tape)',
        choices=medium_block_size_CHOICES,
        default=1024
    )
    default_format = models.IntegerField('Default format', choices=medium_format_CHOICES, default=103)
    min_chunk_size = models.BigIntegerField('Min chunk size', choices=min_chunk_size_CHOICES, default=0)
    min_capacity_warning = models.BigIntegerField('Min capacity warning (0=Disabled)', default=0)
    max_capacity = models.BigIntegerField('Max capacity (0=Disabled)', default=0)
    remote_server = models.CharField('Remote server (https://hostname,user,password)', max_length=255, blank=True)
    master_server = models.CharField('Master server (https://hostname,user,password)', max_length=255, blank=True)
    target = models.CharField('Target (URL, path or barcodeprefix)', max_length=255)

    objects = StorageTargetQueryset.as_manager()

    def get_or_create_storage_medium(self, qs=None):
        if qs is None:
            qs = StorageMedium.objects.all()

        medium = qs.filter(storage_target=self).first()
        if medium is not None:
            return medium, False

        medium = self._create_storage_medium()
        return medium, True

    def _create_storage_medium(self):
        storage_type = get_storage_type_from_medium_type(self.type)
        medium_location = Parameter.objects.get(entity='medium_location').value
        agent = Parameter.objects.get(entity='agent_identifier_value').value

        if storage_type == TAPE:
            slot = TapeSlot.objects.filter(status=20, storage_medium__isnull=True,
                                           medium_id__startswith=self.target
                                           ).exclude(medium_id__exact='').natural_sort().first()
            if slot is None:
                raise ValueError("No tape available for allocation")
            medium = StorageMedium.objects.create(medium_id=slot.medium_id, storage_target=self, status=20,
                                                  location=medium_location, location_status=50,
                                                  block_size=self.default_block_size, format=self.default_format,
                                                  agent=agent, tape_slot=slot)
        elif storage_type == DISK:
            name = 'DISK_{}'.format(self.name)
            medium = StorageMedium.objects.create(medium_id=name, storage_target=self, status=20,
                                                  location=medium_location, location_status=50,
                                                  block_size=self.default_block_size, format=self.default_format,
                                                  agent=agent)
        else:
            raise NotImplementedError()
        return medium

    def get_storage_backend(self):
        storage_type = get_storage_type_from_medium_type(self.type)
        name = get_backend_from_storage_type(storage_type)
        return get_backend(name)()

    class Meta:
        verbose_name = 'Storage Target'
        ordering = ['name']

    def __str__(self):
        if len(self.name):
            return self.name

        return str(self.id)


class StorageMediumQueryset(models.QuerySet):
    def archival_storage(self):
        return self.filter(storage_target__methods__containers=False)

    def secure_storage(self):
        return self.filter(storage_target__methods__containers=True)

    def active(self):
        return self.filter(storage_target__status=True, status__in=[20, 30])

    def readable(self):
        return self.filter(Q(location_status=50) | Q(tape_slot__status=20), status__in=[20, 30])

    def writeable(self):
        return self.filter(status__in=[20], location_status=50)

    def _missing_storage_object_in_other_method_in_policy(self, storage_methods=None, missing_storage=False,
                                                          migration_targets=None, include_inactive_ips=False):
        """
        Returns storage objects that are missing from an
        enabled StorageTarget related to another StorageMethod within the same policy
        """
        search = Q(storage_method=None)
        if migration_targets:
            search = Q()
        elif storage_methods:
            search = Q(storage_method__in=storage_methods)

        qs = StorageObject.objects.filter(
            Exists(
                StorageMethodTargetRelation.objects.annotate(
                    # TODO: Move annotation to filter when the following PR is merged in to stable release:
                    # https://github.com/django/django/pull/12067
                    has_storage_obj=Exists(
                        StorageObject.objects.filter(
                            ip=OuterRef(OuterRef('ip')),
                            storage_medium__storage_target=OuterRef('storage_target'),
                        )
                    ),
                ).filter(
                    search,
                    has_storage_obj=False,
                    status=STORAGE_TARGET_STATUS_ENABLED,
                    storage_method__storage_policies=OuterRef('ip__submission_agreement__policy'),
                )
            ),
            storage_medium=OuterRef('pk'),
        )
        if not include_inactive_ips:
            qs = qs.filter(ip__active=True)
        return Exists(qs)

    def _get_migration_targets(self, policy=''):
        migration_targets = []
        if policy:
            storage_policy_obj = StoragePolicy.objects.get(pk=policy)
            for target in storage_policy_obj.storage_methods.filter(
                enabled=True, storage_method_target_relations__status=STORAGE_TARGET_STATUS_MIGRATE
            ).values_list('targets__pk', flat=True):
                migration_targets.append(target)
        return migration_targets

    def deactivatable(self, include_inactive_ips=False, policy=''):
        if policy:
            migration_targets = self._get_migration_targets(policy)
        else:
            migration_targets = self.filter(
                storage_target__storage_method_target_relations__status=STORAGE_TARGET_STATUS_MIGRATE).values_list(
                    'storage_target__pk', flat=True)
        search = Q()
        if migration_targets:
            search = Q(storage_target__in=migration_targets)
        qs = self.exclude(status=0).filter(
            search,
            ~self._missing_storage_object_in_other_method_in_policy(migration_targets=migration_targets,
                                                                    include_inactive_ips=include_inactive_ips),
            storage_target__storage_method_target_relations__status=STORAGE_TARGET_STATUS_MIGRATE,
        )
        return self.filter(pk__in=qs)

    def migratable(self, export_path='', missing_storage=False, storage_methods=None, policy='',
                   include_inactive_ips=False):

        method_target_rel_with_old_migrate_and_export = StorageMethodTargetRelation.objects.none()
        if export_path:
            method_target_rel_with_old_migrate_and_export = StorageMethodTargetRelation.objects.filter(
                storage_method=Subquery(
                    StorageMethodTargetRelation.objects.filter(
                        storage_target=OuterRef(OuterRef('storage_target')),
                        status=STORAGE_TARGET_STATUS_MIGRATE,
                    ).values('storage_method')[:1]
                )
            )
        if policy:
            migration_targets = self._get_migration_targets(policy)
        else:
            migration_targets = self.filter(
                storage_target__storage_method_target_relations__status=STORAGE_TARGET_STATUS_MIGRATE).values_list(
                    'storage_target__pk', flat=True)
        search = Q()
        if missing_storage:
            if storage_methods:
                storage_targets = []
                _storage_methods = storage_methods
                if isinstance(storage_methods, list):
                    _storage_methods = StorageMethod.objects.filter(
                        pk__in=storage_methods
                    )
                for storage_method in _storage_methods:
                    storage_targets.append(storage_method.targets.get(
                        storage_method_target_relations__status=STORAGE_TARGET_STATUS_ENABLED))
                search = Q(storage_target__in=storage_targets)
            elif policy:
                enabled_targets = []
                storage_policy_obj = StoragePolicy.objects.get(pk=policy)
                storage_methods = storage_policy_obj.storage_methods.filter(
                    enabled=True, storage_method_target_relations__status=STORAGE_TARGET_STATUS_ENABLED
                )
                for target in storage_methods.values_list('targets__pk', flat=True):
                    enabled_targets.append(target)
                search = Q(storage_target__pk__in=enabled_targets)
            else:
                enabled_targets = self.filter(
                    storage_target__storage_method_target_relations__status=STORAGE_TARGET_STATUS_ENABLED).values_list(
                        'storage_target__pk', flat=True)
                search = Q(storage_target__pk__in=enabled_targets)
                migration_targets = enabled_targets
        else:
            if migration_targets:
                search = Q(storage_target__in=migration_targets)

        return self.exclude(status=0).exclude(storage_target__type__gte=300, tape_slot__isnull=True).filter(
            Q(
                Q(self._missing_storage_object_in_other_method_in_policy(storage_methods=storage_methods,
                                                                         missing_storage=missing_storage,
                                                                         migration_targets=migration_targets,
                                                                         include_inactive_ips=include_inactive_ips)) |
                Q(Exists(method_target_rel_with_old_migrate_and_export))
            ) &
            search
        )

    def non_migratable(self):
        return self.exclude(pk__in=self.migratable())

    def natural_sort(self, column='medium_id'):
        return natural_sort(self, column)

    def fastest(self):
        container = Case(
            When(storage_target__methods__containers=False, then=Value(1)),
            When(storage_target__methods__containers=True, then=Value(2)),
            output_field=IntegerField(),
        )
        remote = Case(
            When(storage_target__remote_server__isnull=True, then=Value(1)),
            When(storage_target__remote_server__isnull=False, then=Value(2)),
            output_field=IntegerField(),
        )
        storage_type = Case(
            When(storage_target__methods__type=DISK, then=Value(1)),
            When(storage_target__methods__type=TAPE, then=Value(2)),
            output_field=IntegerField(),
        )
        return self.annotate(
            container_order=container,
            remote=remote,
            storage_type=storage_type
        ).order_by('remote', 'container_order', 'storage_type')


class StorageMedium(models.Model):
    "A single storage medium (device)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    medium_id = models.CharField("The id for the medium, e.g. barcode", max_length=255, unique=True)
    status = models.IntegerField(choices=medium_status_CHOICES, db_index=True)
    location = models.CharField(max_length=255)
    location_status = models.IntegerField(choices=medium_location_status_CHOICES)
    block_size = models.IntegerField(choices=medium_block_size_CHOICES)
    format = models.IntegerField(choices=medium_format_CHOICES)
    used_capacity = models.BigIntegerField(default=0)
    num_of_mounts = models.IntegerField(default=0)

    create_date = models.DateTimeField(default=timezone.now)
    last_changed_local = models.DateTimeField(auto_now=True)
    last_changed_external = models.DateTimeField(null=True)

    agent = models.CharField(max_length=255)
    storage_target = models.ForeignKey('StorageTarget', on_delete=models.CASCADE)
    tape_slot = models.OneToOneField(
        'TapeSlot',
        models.SET_NULL,
        related_name='storage_medium',
        null=True,
        blank=True,
    )
    tape_drive = models.OneToOneField(
        'TapeDrive',
        models.SET_NULL,
        related_name='storage_medium',
        null=True,
        blank=True,
    )

    objects = StorageMediumQueryset.as_manager()

    @classmethod
    @transaction.atomic
    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logging.getLogger('essarch.storage.models'),
                                                              logging.DEBUG))
    def create_from_remote_copy(cls, host, session, object_id, create_tape_drive=False, create_tape_slot=False):
        remote_obj_url = urljoin(host, reverse('storagemedium-detail', args=(object_id,)))
        r = session.get(remote_obj_url, timeout=60)
        r.raise_for_status()

        data = r.json()
        data.pop('location_status_display', None)
        data.pop('status_display', None)
        data.pop('block_size_display', None)
        data.pop('format_display', None)
        data['storage_target_id'] = data.pop('storage_target')['id']
        if data.get('tape_drive') is not None and create_tape_drive:
            data['tape_drive'] = TapeDrive.create_from_remote_copy(
                host, session, data['tape_drive'], create_storage_medium=False
            )
        else:
            data.pop('tape_drive', None)
        if data.get('tape_slot') is not None and create_tape_slot:
            data['tape_slot'] = TapeSlot.create_from_remote_copy(
                host, session, data['tape_slot'], create_storage_medium=False
            )
        else:
            data.pop('tape_slot', None)
        data['last_changed_local'] = timezone.now
        storage_medium, _ = StorageMedium.objects.update_or_create(
            pk=data.pop('id'),
            medium_id=data.pop('medium_id'),
            defaults=data,
        )
        return storage_medium

    def get_type(self):
        return get_storage_type_from_medium_type(self.storage_target.type)

    def prepare_for_read(self, io_lock_key=None):
        storage_backend = self.storage_target.get_storage_backend()
        if storage_backend.type == 300:
            storage_backend.prepare_for_read(self, io_lock_key)
        else:
            storage_backend.prepare_for_read(self)

    def prepare_for_write(self, io_lock_key=None):
        storage_backend = self.storage_target.get_storage_backend()
        if storage_backend.type == 300:
            storage_backend.prepare_for_write(self, io_lock_key)
        else:
            storage_backend.prepare_for_write(self)

    def is_migrated(self, include_inactive_ips=False) -> True:
        return self in StorageMedium.objects.deactivatable(include_inactive_ips=include_inactive_ips)

    def deactivate(self) -> None:
        self.status = 0
        self.save()

    def mark_as_full(self):
        logger = logging.getLogger('essarch.storage.models')
        logger.debug('Marking storage medium as full: "{}"'.format(str(self.pk)))
        logger.info('Storage medium is full, start to verify: "{}"'.format(self.medium_id))
        objs = self.storage.annotate(
            content_location_value_int=Cast('content_location_value', models.IntegerField())
        ).order_by('content_location_value_int')

        if objs.count() > 3:
            objs = [objs.first(), objs[int(objs.count() / 2)], objs.last()]

        try:
            for obj in objs:
                obj.verify()
        except AssertionError:
            self.status = 100
            logger.exception('Failed to verify storage medium: "{}"'.format(str(self.pk)))
            raise
        else:
            verifydir = Path.objects.get(entity='verify').value
            tmppath = os.path.join(verifydir, self.storage_target.target)
            shutil.rmtree(tmppath)
            self.status = 30
            storage_backend = self.storage_target.get_storage_backend()
            storage_backend.post_mark_as_full(self)
        finally:
            self.save(update_fields=['status'])
            logger.info('Storage medium is full, content verified success: "{}"'.format(self.medium_id))

    class Meta:
        permissions = (
            ("list_storageMedium", "Can list storageMedium"),  # TODO: replace with view_storagemedium
        )

    def __str__(self):
        if len(self.medium_id):
            return self.medium_id

        return str(self.id)

    def check_db_sync(self):
        if self.last_changed_local is not None and self.last_changed_external is not None:
            return (self.last_changed_local - self.last_changed_external).total_seconds() == 0

        return False


class StorageObjectQueryset(models.QuerySet):
    def archival_storage(self):
        return self.filter(container=False)

    def secure_storage(self):
        return self.filter(container=True)

    def readable(self):
        return self.filter(
            Q(storage_medium__location_status=50) | Q(storage_medium__tape_slot__status=20),
            storage_medium__storage_target__status=True,
            storage_medium__storage_target__storage_method_target_relations__status__in=[
                STORAGE_TARGET_STATUS_ENABLED, STORAGE_TARGET_STATUS_READ_ONLY,
                STORAGE_TARGET_STATUS_MIGRATE,
            ],
            storage_medium__storage_target__storage_method_target_relations__storage_method__enabled=True,
            storage_medium__status__in=[20, 30]
        )

    def natural_sort(self, column='content_location_value'):
        return natural_sort(self, column)

    def fastest(self):
        container = Case(
            When(container=False, then=Value(1)),
            When(container=True, then=Value(2)),
            output_field=IntegerField(),
        )
        remote = Case(
            When((Q(storage_medium__storage_target__remote_server=None) |
                  Q(storage_medium__storage_target__remote_server='')), then=Value(1)),
            When(~(Q(storage_medium__storage_target__remote_server=None) |
                   Q(storage_medium__storage_target__remote_server='')), then=Value(2)),
            output_field=IntegerField(),
        )
        storage_type = Case(
            When(content_location_type=DISK, then=Value(1)),
            When(content_location_type=TAPE, then=Value(2)),
            output_field=IntegerField(),
        )
        content_location_value_int = Case(
            When(content_location_type=TAPE, then=Cast('content_location_value', models.IntegerField())),
            default=Value(0),
            output_field=IntegerField(),
        )
        return self.annotate(
            container_order=container,
            remote=remote,
            storage_type=storage_type,
            content_location_value_int=content_location_value_int,
        ).order_by('remote', 'container_order', 'storage_type',
                   'storage_medium__medium_id', 'content_location_value_int')


class StorageObject(models.Model):
    """The stored representation of an archive object on a storage medium"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    container = models.BooleanField(default=False)
    content_location_type = models.IntegerField(choices=storage_type_CHOICES)
    content_location_value = models.CharField(max_length=255, blank=True)

    last_changed_local = models.DateTimeField(default=timezone.now)
    last_changed_external = models.DateTimeField(null=True)

    ip = models.ForeignKey('ip.InformationPackage', on_delete=models.CASCADE, related_name='storage',
                           verbose_name='information package')
    storage_medium = models.ForeignKey('StorageMedium', on_delete=models.CASCADE, related_name='storage',
                                       verbose_name='medium')

    objects = StorageObjectQueryset.as_manager()

    @classmethod
    @transaction.atomic
    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logging.getLogger('essarch.storage.models'),
                                                              logging.DEBUG))
    def create_from_remote_copy(cls, host, session, object_id):
        remote_obj_url = urljoin(host, reverse('storageobject-detail', args=(object_id,)))
        r = session.get(remote_obj_url, timeout=60)
        r.raise_for_status()

        data = r.json()
        data['ip_id'] = data.pop('ip')
        data['storage_medium'] = StorageMedium.create_from_remote_copy(
            host, session, data['storage_medium']
        )
        data.pop('medium_id', None)
        data.pop('target_name', None)
        data.pop('target_target', None)
        data.pop('ip_object_identifier_value', None)
        data.pop('ip_object_size', None)
        data['last_changed_local'] = timezone.now
        obj, _ = StorageObject.objects.update_or_create(
            pk=data.pop('id'),
            defaults=data,
        )
        return obj

    def get_root(self):
        target = self.storage_medium.storage_target.target
        if self.content_location_value == '':
            target = os.path.join(target, self.ip.object_identifier_value)
            if self.container:
                target += '.tar'
        else:
            target = os.path.join(target, self.content_location_value)
        return target

    def get_full_path(self):
        return os.path.join(self.get_root())

    def get_storage_backend(self):
        return self.storage_medium.storage_target.get_storage_backend()

    def readable(self):
        if self.storage_medium.tape_slot is not None and self.storage_medium.tape_slot.status == 20:
            tape_in_tape_slot = True
        else:
            tape_in_tape_slot = False

        return all((
            self.storage_medium.storage_target.status,
            self.storage_medium.storage_target.storage_method_target_relations.filter(
                status__in=[
                    STORAGE_TARGET_STATUS_ENABLED, STORAGE_TARGET_STATUS_READ_ONLY,
                    STORAGE_TARGET_STATUS_MIGRATE,
                ],
                storage_method__enabled=True,
            ),
            self.storage_medium.status in [20, 30],
        )) and (self.storage_medium.location_status == 50 or tape_in_tape_slot)

    def is_cache_for_ip(self, ip):
        return self.storage_medium.storage_target.storage_method_target_relations.filter(
            storage_method=ip.policy.cache_storage,
            status__in=[STORAGE_TARGET_STATUS_ENABLED, STORAGE_TARGET_STATUS_READ_ONLY],
        ).exists()

    def open(self, path, *args, **kwargs):
        backend = self.get_storage_backend()
        return backend.open(self, path, *args, **kwargs)

    def read(self, dst, task, extract=False, local=True):
        logger = logging.getLogger('essarch.storage.models')
        ip = self.ip
        is_cached_storage_object = self.is_cache_for_ip(ip)

        storage_medium = self.storage_medium
        storage_target = storage_medium.storage_target

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

            if task.status in celery_states.EXCEPTION_STATES:
                task.reraise()
        else:
            storage_backend = self.get_storage_backend()
            storage_medium.prepare_for_read(io_lock_key=self)

            if storage_target.master_server and local is False:
                # we are on a remote host that has been requested
                # by master to write to its temp directory
                temp_dir = Path.objects.get(entity='temp').value

                session = requests.Session()
                session.verify = settings.REQUESTS_VERIFY
                server_list = storage_target.master_server.split(',')
                if len(server_list) == 2:
                    host, token = server_list
                    session.headers['Authorization'] = 'Token %s' % token
                else:
                    host, user, passw = server_list
                    session.auth = (user, passw)
                session.params = {'dst': dst}

                temp_object_path = ip.get_temp_object_path()
                temp_container_path = ip.get_temp_container_path()
                temp_mets_path = ip.get_temp_container_xml_path()
                temp_aic_mets_path = ip.get_temp_container_aic_xml_path()
                dst = urljoin(host, reverse('informationpackage-add-file-from-master'))

                storage_backend.read(self, temp_dir, extract=extract)

                if is_cached_storage_object or not self.container:
                    with tarfile.open(temp_container_path, 'w') as new_tar:
                        new_tar.format = settings.TARFILE_FORMAT
                        new_tar.add(temp_object_path)
                    copy_file(temp_container_path, dst, requests_session=session)
                    delete_path(temp_container_path)

                else:
                    copy_file(temp_container_path, dst, requests_session=session)
                    copy_file(temp_mets_path, dst, requests_session=session)
                    copy_file(temp_aic_mets_path, dst, requests_session=session)
                    delete_path(temp_container_path)
                    delete_path(temp_mets_path)
                    delete_path(temp_aic_mets_path)

            else:
                storage_backend.read(self, dst, extract=extract)

    def list_files(self, pattern=None, case_sensitive=True):
        backend = self.get_storage_backend()
        return backend.list_files(self, pattern=pattern, case_sensitive=case_sensitive)

    def delete_files(self):
        backend = self.get_storage_backend()
        backend.delete(self)

    class Meta:
        permissions = (
            ("list_storage", "Can list storage"),
            ("storage_migration", "Storage migration"),
            ("storage_maintenance", "Storage maintenance"),
            ("storage_management", "Storage management"),
        )

    def verify(self):
        if self.content_location_type == TAPE:
            verifydir = Path.objects.get(entity='verify').value
            tmppath = os.path.join(verifydir, self.storage_medium.storage_target.target)

            if not os.path.exists(tmppath):
                try:
                    os.mkdir(tmppath)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise

            drive = self.storage_medium.tape_drive
            if drive is None:
                raise ValueError("Tape not mounted")

            set_tape_file_number(drive.device, int(self.content_location_value))
            read_tape(drive.device, path=tmppath, block_size=self.storage_medium.block_size * 512)

            drive.last_change = timezone.now()
            drive.save(update_fields=['last_change'])

            filename = os.path.join(tmppath, self.ip.object_identifier_value + '.tar')
            algorithm = self.ip.get_message_digest_algorithm_display()
            options = {'expected': self.ip.message_digest, 'algorithm': algorithm}

            validator = ChecksumValidator(context='checksum_str', options=options)
            validator.validate(filename)

    def __str__(self):
        try:
            medium_id = self.storage_medium.medium_id
        except ObjectDoesNotExist:
            medium_id = 'unknown media'

        try:
            obj_identifier_value = self.ip.object_identifier_value
        except ObjectDoesNotExist:
            obj_identifier_value = 'unknown object'

        return '%s @ %s' % (obj_identifier_value, medium_id)

    def check_db_sync(self):
        if self.last_changed_local is not None and self.last_changed_external is not None:
            return (self.last_changed_local - self.last_changed_external).total_seconds() == 0

        return False


class TapeDrive(models.Model):
    STATUS_CHOICES = (
        (0, 'Inactive'),
        (20, 'Ok'),
        (100, 'FAIL'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    drive_id = models.IntegerField()
    device = models.CharField(max_length=255, unique=True)
    io_queue_entry = models.OneToOneField('IOQueue', models.PROTECT, related_name='tape_drive', null=True, blank=True)
    num_of_mounts = models.IntegerField(default=0)
    idle_time = models.DurationField(default=timedelta(hours=1))
    last_change = models.DateTimeField(default=timezone.now)
    robot = models.ForeignKey('Robot', models.PROTECT, related_name='tape_drives')
    locked = models.BooleanField(default=False)
    status = models.IntegerField(choices=STATUS_CHOICES, default=20)

    @classmethod
    def clear_locks(cls):
        return cache.delete_pattern(DRIVE_LOCK_PREFIX + '*')

    def clear_lock(self):
        self.locked = False
        self.save()
        return cache.delete_pattern(self.get_lock_key())

    def get_lock_key(self):
        return '{}{}'.format(DRIVE_LOCK_PREFIX, str(self.pk))

    def is_locked(self):
        return self.get_lock_key() in cache

    def locked_by(self):
        if self.is_locked():
            return pickle.loads(cache.get(self.get_lock_key()))
        elif self.locked:
            return 'robot'
        else:
            return ''

    @classmethod
    @transaction.atomic
    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logging.getLogger('essarch.storage.models'),
                                                              logging.DEBUG))
    def create_from_remote_copy(cls, host, session, object_id, create_storage_medium=True):
        remote_obj_url = urljoin(host, reverse('tapedrive-detail', args=(object_id,)))
        r = session.get(remote_obj_url, timeout=60)
        r.raise_for_status()

        data = r.json()
        data.pop('status_display', None)
        data.pop('idle_timer', None)
        data.pop('idle_time', None)

        data['robot'] = Robot.create_from_remote_copy(
            host, session, data['robot']
        )
        if not create_storage_medium:
            data.pop('storage_medium', None)

        tape_drive, _ = TapeDrive.objects.update_or_create(
            pk=data.pop('id'),
            defaults=data,
        )
        return tape_drive

    def __str__(self):
        return self.device


class TapeSlotQueryset(models.QuerySet):
    def natural_sort(self, column='medium_id'):
        return natural_sort(self, column)


class TapeSlot(models.Model):
    STATUS_CHOICES = (
        (0, 'Inactive'),
        (20, 'Ok'),
        (100, 'FAIL'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slot_id = models.IntegerField()
    medium_id = models.CharField(
        "The id for the medium, e.g. barcode",
        max_length=255,
        blank=True,
        null=True,
    )
    robot = models.ForeignKey('Robot', models.PROTECT, related_name='tape_slots')
    status = models.IntegerField(choices=STATUS_CHOICES, default=20)

    objects = TapeSlotQueryset.as_manager()

    @classmethod
    @transaction.atomic
    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logging.getLogger('essarch.storage.models'),
                                                              logging.DEBUG))
    def create_from_remote_copy(cls, host, session, object_id, create_storage_medium=True):
        remote_obj_url = urljoin(host, reverse('tapeslot-detail', args=(object_id,)))
        r = session.get(remote_obj_url, timeout=60)
        r.raise_for_status()

        data = r.json()
        data.pop('locked', None)
        data.pop('mounted', None)
        data.pop('status_display', None)

        data['robot'] = Robot.create_from_remote_copy(
            host, session, data['robot']
        )
        if not create_storage_medium:
            data.pop('storage_medium', None)

        tape_slot, _ = TapeSlot.objects.update_or_create(
            pk=data.pop('id'),
            defaults=data,
        )
        return tape_slot

    class Meta:
        ordering = ('slot_id',)
        unique_together = [['slot_id', 'robot'], ['medium_id', 'robot']]

    def __str__(self):
        return str(self.slot_id)


class Robot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField("Describing label for the robot", max_length=255, blank=True)
    device = models.CharField(max_length=255, unique=True)
    online = models.BooleanField(default=False)

    @classmethod
    @transaction.atomic
    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logging.getLogger('essarch.storage.models'),
                                                              logging.DEBUG))
    def create_from_remote_copy(cls, host, session, object_id):
        remote_obj_url = urljoin(host, reverse('robot-detail', args=(object_id,)))
        r = session.get(remote_obj_url, timeout=60)
        r.raise_for_status()

        data = r.json()
        robot, _ = Robot.objects.update_or_create(
            pk=data.pop('id'),
            defaults=data,
        )
        return robot

    def __str__(self):
        return self.label


class RobotQueue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.PROTECT, related_name='robot_queue_entries')
    posted = models.DateTimeField(default=timezone.now)
    robot = models.ForeignKey('Robot', on_delete=models.CASCADE, related_name='robot_queue', null=True)
    io_queue_entry = models.ForeignKey('IOQueue', models.SET_NULL, blank=True, null=True)
    storage_medium = models.ForeignKey('StorageMedium', models.PROTECT)
    tape_drive = models.ForeignKey('TapeDrive', models.CASCADE, blank=True, null=True)
    req_type = models.IntegerField(choices=robot_req_type_CHOICES)
    status = models.IntegerField(default=0, choices=req_status_CHOICES)

    class Meta:
        get_latest_by = 'posted'


class IOQueue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    req_type = models.IntegerField(choices=IOReqType_CHOICES)
    req_purpose = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey('auth.User', on_delete=models.PROTECT, related_name='io_queues')
    object_path = models.CharField(max_length=256, blank=True)
    write_size = models.BigIntegerField(null=True, blank=True)
    result = PickledObjectField(blank=True, null=True)
    status = models.IntegerField(blank=True, default=0, choices=req_status_CHOICES)
    task_id = models.CharField(max_length=36, blank=True)
    posted = models.DateTimeField(default=timezone.now)
    ip = models.ForeignKey('ip.InformationPackage', on_delete=models.CASCADE, null=True)
    storage_method_target = models.ForeignKey('StorageMethodTargetRelation', on_delete=models.CASCADE)
    storage_medium = models.ForeignKey('StorageMedium', on_delete=models.CASCADE, blank=True, null=True)
    storage_object = models.ForeignKey('StorageObject', on_delete=models.CASCADE, blank=True, null=True)
    access_queue = models.ForeignKey('AccessQueue', on_delete=models.CASCADE, blank=True, null=True)
    remote_status = models.IntegerField(blank=True, default=0, choices=remote_status_CHOICES)
    transfer_task_id = models.CharField(max_length=36, blank=True)
    step = models.ForeignKey('WorkflowEngine.ProcessStep', on_delete=models.SET_NULL, null=True)

    class Meta:
        get_latest_by = 'posted'
        permissions = (
            ("list_IOQueue", "Can list IOQueue"),
        )

    @property
    def remote_io(self):
        master_server = self.storage_method_target.storage_target.master_server
        return len(master_server.split(',')) > 1

    @retry(reraise=True, stop=stop_after_attempt(5), wait=wait_fixed(60))
    def sync_with_master(self, data):
        master_server = self.storage_method_target.storage_target.master_server
        session = requests.Session()
        session.verify = settings.REQUESTS_VERIFY
        server_list = master_server.split(',')
        if len(server_list) == 2:
            host, token = server_list
            session.headers['Authorization'] = 'Token %s' % token
        else:
            host, user, passw = server_list
            session.auth = (user, passw)
        dst = urljoin(host, 'api/io-queue/%s/' % self.pk)

        try:
            data['storage_object']['storage_medium'].pop('tape_slot')
        except KeyError:
            pass

        try:
            data['storage_object']['storage_medium'].pop('tape_drive')
        except KeyError:
            pass

        response = session.patch(dst, json=data)
        response.raise_for_status()


class AccessQueue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package = models.BooleanField(default=True)
    extracted = models.BooleanField(default=False)
    new = models.BooleanField(default=False)
    package_xml = models.BooleanField(default=False)
    aic_xml = models.BooleanField(default=False)
    object_identifier_value = models.CharField(max_length=255, blank=True)
    req_purpose = models.CharField(max_length=255)
    user = models.ForeignKey('auth.User', on_delete=models.PROTECT, related_name='access_queues')
    ip = models.ForeignKey('ip.InformationPackage', on_delete=models.CASCADE, null=False, related_name='access_queues')
    new_ip = models.ForeignKey(
        'ip.InformationPackage',
        on_delete=models.CASCADE,
        null=True,
        related_name='access_queues_new_ip'
    )
    status = models.IntegerField(null=True, blank=True, default=0, choices=req_status_CHOICES)
    path = models.CharField(max_length=255)
    posted = models.DateTimeField(default=timezone.now)

    class Meta:
        get_latest_by = 'posted'
        permissions = (
            ("list_accessqueue", "Can list access queue"),
        )
