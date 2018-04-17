from __future__ import unicode_literals

import errno
import os
import uuid
from datetime import timedelta

import requests
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Case, When, Value, IntegerField
from django.db.models.functions import Cast
from picklefield.fields import PickledObjectField
from retrying import retry
from six.moves import urllib

from ESSArch_Core.WorkflowEngine.models import ProcessTask
from ESSArch_Core.configuration.models import Path
from ESSArch_Core.fixity.validation.backends.checksum import ChecksumValidator
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.storage.backends import get_backend

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
    (30, 'unmount (force)'),
)

medium_type_CHOICES = (
    (200, 'DISK'),
    (301, 'IBM-LTO1'),
    (302, 'IBM-LTO2'),
    (303, 'IBM-LTO3'),
    (304, 'IBM-LTO4'),
    (305, 'IBM-LTO5'),
    (306, 'IBM-LTO6'),
    (325, 'HP-LTO5'),
    (326, 'HP-LTO6'),
    (401, 'HDFS'),
    (402, 'HDFS-REST'),
)

storage_type_CHOICES = (
    (DISK, 'DISK'),
    (TAPE, 'TAPE'),
    (CAS, 'CAS'),
)

medium_format_CHOICES = (
    (103, '103 (AIC support)'),
    (102, '102 (Media label)'),
    (101, '101 (Old read only)'),
    (100, '100 (Old read only)'),
)

medium_status_CHOICES = (
    (0, 'Inactive'),
    (20, 'Write'),
    (30, 'Full'),
    (100, 'FAIL'),
)

medium_location_status_CHOICES = (
    (10, 'Delivered'),
    (20, 'Received'),
    (30, 'Placed'),
    (40, 'Collected'),
    (50, 'Robot'),
)

medium_block_size_CHOICES = (
    (128, '64K'),
    (250, '125K'),
    (256, '128K'),
    (512, '256K'),
    (1024, '512K'),
    (2048, '1024K'),
)

storage_target_status_CHOICES = (
    (0, 'Disabled'),
    (1, 'Enabled'),
    (2, 'ReadOnly'),
    (3, 'Migrate'),
)

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


def get_backend_from_storage_type(type):
    return {
        DISK: 'disk',
        TAPE: 'tape',
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


class StorageMethod(models.Model):
    """Disk, tape or CAS"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('Name', max_length=255, blank=True)
    status = models.BooleanField('Storage method status', default=False)
    type = models.IntegerField('Type', choices=storage_type_CHOICES, default=200)
    containers = models.BooleanField(default=False)
    archive_policy = models.ForeignKey('configuration.ArchivePolicy', related_name='storage_methods')
    targets = models.ManyToManyField('StorageTarget', through='StorageMethodTargetRelation', related_name='methods')

    objects = StorageMethodQueryset.as_manager()

    @property
    def active_targets(self):
        return StorageTarget.objects.filter(
            storagemethodtargetrelation__storage_method=self,
            storagemethodtargetrelation__status=1
        )

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        if len(self.name):
            return self.name

        return unicode(self.id)


class StorageMethodTargetRelation(models.Model):
    """Relation between StorageMethod and StorageTarget"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('Name', max_length=255, blank=True)
    status = models.IntegerField('Storage target status', choices=storage_target_status_CHOICES, default=0)
    storage_target = models.ForeignKey('StorageTarget', related_name='storage_method_target_relations')
    storage_method = models.ForeignKey('StorageMethod', related_name='storage_method_target_relations')

    class Meta:
        verbose_name = 'Storage Target/Method Relation'
        ordering = ['name']

    def __unicode__(self):
        if len(self.name):
            return self.name

        return unicode(self.id)


class StorageTarget(models.Model):
    """A series of tapes or a single disk"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('Name', max_length=255, unique=True)
    status = models.BooleanField('Storage target status', default=True)
    type = models.IntegerField('Type', choices=medium_type_CHOICES, default=200)
    default_block_size = models.IntegerField('Default block size (tape)', choices=medium_block_size_CHOICES, default=1024)
    default_format = models.IntegerField('Default format', choices=medium_format_CHOICES, default=103)
    min_chunk_size = models.BigIntegerField('Min chunk size', choices=min_chunk_size_CHOICES, default=0)
    min_capacity_warning = models.BigIntegerField('Min capacity warning (0=Disabled)', default=0)
    max_capacity = models.BigIntegerField('Max capacity (0=Disabled)', default=0)
    remote_server = models.CharField('Remote server (https://hostname,user,password)', max_length=255, blank=True)
    master_server = models.CharField('Master server (https://hostname,user,password)', max_length=255, blank=True)
    target = models.CharField('Target (URL, path or barcodeprefix)', max_length=255)

    def get_storage_backend(self):
        storage_type = get_storage_type_from_medium_type(self.type)
        name = get_backend_from_storage_type(storage_type)
        return get_backend(name)()

    class Meta:
        verbose_name = 'Storage Target'
        ordering = ['name']

    def __unicode__(self):
        if len(self.name):
            return self.name

        return unicode(self.id)


class StorageMediumQueryset(models.QuerySet):
    def archival_storage(self):
        return self.filter(storage_target__methods__containers=False)

    def secure_storage(self):
        return self.filter(storage_target__methods__containers=True)

    def readable(self):
        return self.filter(status__in=[20, 30], location_status=50)

    def writeable(self):
        return self.filter(status__in=[20], location_status=50)

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
    status = models.IntegerField(choices=medium_status_CHOICES)
    location = models.CharField(max_length=255)
    location_status = models.IntegerField(choices=medium_location_status_CHOICES)
    block_size = models.IntegerField(choices=medium_block_size_CHOICES)
    format = models.IntegerField(choices=medium_format_CHOICES)
    used_capacity = models.BigIntegerField(default=0)
    num_of_mounts = models.IntegerField(default=0)

    create_date = models.DateTimeField(auto_now_add=True)
    last_changed_local = models.DateTimeField(null=True)
    last_changed_external = models.DateTimeField(null=True)

    agent = models.ForeignKey('auth.User', on_delete=models.PROTECT)
    storage_target = models.ForeignKey('StorageTarget')
    tape_slot = models.OneToOneField('TapeSlot', models.PROTECT, related_name='storage_medium', null=True, blank=True)
    tape_drive = models.OneToOneField('TapeDrive', models.PROTECT, related_name='storage_medium', null=True, blank=True)

    objects = StorageMediumQueryset.as_manager()

    def get_type(self):
        target_type = self.storage_target.type
        if target_type < 300:
            return DISK
        elif target_type < 400:
            return TAPE
        else:
            return CAS

    def mark_as_full(self):
        objs = self.storage.annotate(
            content_location_value_int=Cast('content_location_value', models.IntegerField())
        ).order_by('content_location_value_int')

        if objs.count() > 3:
            objs = [objs.first(), objs[objs.count()/2], objs.last()]

        try:
            for obj in objs:
                obj.verify()
        except AssertionError:
            self.status = 100
            raise
        else:
            self.status = 30
        finally:
            self.save(update_fields=['status'])

    class Meta:
        permissions = (
            ("list_storageMedium", "Can list storageMedium"),
        )

    def __unicode__(self):
        if len(self.medium_id):
            return self.medium_id

        return unicode(self.id)

    def check_db_sync(self):
        if self.last_changed_local is not None and self.last_changed_external is not None:
            return (self.last_changed_local-self.last_changed_external).total_seconds() == 0

        return False


class StorageObjectQueryset(models.QuerySet):
    def archival_storage(self):
        return self.filter(container=False)

    def secure_storage(self):
        return self.filter(container=True)

    def readable(self):
        return self.filter(storage_medium__status__in=[20, 30], storage_medium__location_status=50)

    def fastest(self):
        container = Case(
            When(container=False, then=Value(1)),
            When(container=True, then=Value(2)),
            output_field=IntegerField(),
        )
        remote = Case(
            When(storage_medium__storage_target__remote_server__isnull=True, then=Value(1)),
            When(storage_medium__storage_target__remote_server__isnull=False, then=Value(2)),
            output_field=IntegerField(),
        )
        storage_type = Case(
            When(content_location_type=DISK, then=Value(1)),
            When(content_location_type=TAPE, then=Value(2)),
            output_field=IntegerField(),
        )
        return self.annotate(
            container_order=container,
            remote=remote,
            storage_type=storage_type
        ).order_by('remote', 'container_order', 'storage_type')


class StorageObject(models.Model):
    """The stored representation of an archive object on a storage medium"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    container = models.BooleanField(default=False)
    content_location_type = models.IntegerField(choices=storage_type_CHOICES)
    content_location_value = models.CharField(max_length=255, blank=True)

    last_changed_local = models.DateTimeField(null=True, auto_now_add=True)
    last_changed_external = models.DateTimeField(null=True)

    ip = models.ForeignKey(InformationPackage, related_name='storage')
    storage_medium = models.ForeignKey('StorageMedium', related_name='storage')

    objects = StorageObjectQueryset.as_manager()

    def get_root(self):
        target = self.storage_medium.storage_target.target
        if self.content_location_value == '':
            target = os.path.join(target, self.ip.object_identifier_value)
            if self.container:
                target += '.tar'
        else:
            return os.path.join(target, self.content_location_value)
        return target

    def get_full_path(self):
        return os.path.join(self.get_root())

    def get_storage_backend(self):
        return self.storage_medium.storage_target.get_storage_backend()

    def extract(self):
        if not self.container:
            raise ValueError("Not a container")

        policy = self.ip.policy
        target_medium = StorageMedium.objects.archival_storage().writeable().fastest().filter(
            storage_target__methods__archive_policy=policy).first()

        if target_medium is None:
            raise ValueError("No writeable archival storage configured for IP")

        backend = self.get_storage_backend()
        target_path = backend.read(self, target_medium.storage_target.target, extract=True, include_xml=False)
        medium_type = target_medium.get_type()
        new_obj = StorageObject.objects.create(ip=self.ip, storage_medium=target_medium, container=False,
                                               content_location_type=medium_type, content_location_value=target_path)
        return new_obj

    def read(self, path):
        if not self.container:
            backend = self.get_storage_backend()
            with backend.open(self, path) as fp:
                return fp

        extracted = self.extract()
        return extracted.read(path)

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

            ProcessTask.objects.create(
                name='ESSArch_Core.tasks.SetTapeFileNumber',
                params={
                    'medium': self.storage_medium_id,
                    'num': int(self.content_location_value)
                },
                information_package=self.ip,
            ).run().get()

            ProcessTask.objects.create(
                name='ESSArch_Core.tasks.ReadTape',
                params={
                    'medium': self.storage_medium_id,
                    'path': tmppath,
                    'block_size': self.storage_medium.block_size * 512,
                },
                information_package=self.ip,
            ).run().get()

            filename = os.path.join(tmppath, self.ip.object_identifier_value + '.tar'),
            algorithm = self.ip.get_message_digest_algorithm_display()
            options = {'expected': self.ip.message_digest, 'algorithm': algorithm}

            validator = ChecksumValidator(context='checksum_str', options=options)
            validator.validate(filename)

    def __unicode__(self):
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
            return (self.last_changed_local-self.last_changed_external).total_seconds() == 0

        return False


class TapeDrive(models.Model):
    STATUS_CHOICES = (
        (0, 'Inactive'),
        (20, 'Write'),
        (100, 'FAIL'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    drive_id = models.IntegerField()
    device = models.CharField(max_length=255, unique=True)
    io_queue_entry = models.OneToOneField('IOQueue', models.PROTECT, related_name='tape_drive', null=True)
    num_of_mounts = models.IntegerField(default=0)
    idle_time = models.DurationField(default=timedelta(hours=1))
    last_change = models.DateTimeField(auto_now_add=True)
    robot = models.ForeignKey('Robot', models.PROTECT, related_name='tape_drives')
    locked = models.BooleanField(default=False)
    status = models.IntegerField(choices=STATUS_CHOICES, default=20)

    def __unicode__(self):
        return self.device

class TapeSlot(models.Model):
    STATUS_CHOICES = (
        (0, 'Inactive'),
        (20, 'Write'),
        (100, 'FAIL'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slot_id = models.IntegerField()
    medium_id = models.CharField("The id for the medium, e.g. barcode", max_length=255, unique=True, blank=True, null=True)
    robot = models.ForeignKey('Robot', models.PROTECT, related_name='tape_slots')
    status = models.IntegerField(choices=STATUS_CHOICES, default=20)

    class Meta:
        unique_together = ('slot_id', 'robot')

    def __unicode__(self):
        return unicode(self.slot_id)


class Robot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField("Describing label for the robot", max_length=255, blank=True)
    device = models.CharField(max_length=255, unique=True)
    online = models.BooleanField(default=False)

    def __unicode__(self):
        return self.label


class RobotQueue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.PROTECT, related_name='robot_queue_entries')
    posted = models.DateTimeField(auto_now_add=True)
    robot = models.OneToOneField('Robot', related_name='robot_queue', null=True)
    io_queue_entry = models.ForeignKey('IOQueue', models.PROTECT, null=True)
    storage_medium = models.ForeignKey('StorageMedium', models.PROTECT)
    tape_drive = models.ForeignKey('TapeDrive', models.CASCADE, null=True)
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
    result = PickledObjectField(blank=True)
    status = models.IntegerField(blank=True, default=0, choices=req_status_CHOICES)
    task_id = models.CharField(max_length=36, blank=True)
    posted = models.DateTimeField(auto_now_add=True)
    ip = models.ForeignKey(InformationPackage, null=True)
    storage_method_target = models.ForeignKey('StorageMethodTargetRelation')
    storage_medium = models.ForeignKey('StorageMedium', blank=True, null=True)
    storage_object = models.ForeignKey('StorageObject', blank=True, null=True)
    access_queue = models.ForeignKey('AccessQueue', blank=True, null=True)
    remote_status = models.IntegerField(blank=True, default=0, choices=remote_status_CHOICES)
    transfer_task_id = models.CharField(max_length=36, blank=True)
    step = models.ForeignKey('WorkflowEngine.ProcessStep', on_delete=models.PROTECT, null=True)

    class Meta:
        get_latest_by = 'posted'
        permissions = (
            ("list_IOQueue", "Can list IOQueue"),
        )

    @property
    def remote_io(self):
        master_server = self.storage_method_target.storage_target.master_server
        return len(master_server.split(',')) == 3

    @retry(stop_max_attempt_number=5, wait_fixed=60000)
    def sync_with_master(self, data):
        master_server = self.storage_method_target.storage_target.master_server
        host, user, passw = master_server.split(',')
        dst = urllib.parse.urljoin(host, 'api/io-queue/%s/' % self.pk)

        session = requests.Session()
        session.verify = False
        session.auth = (user, passw)

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
    ip = models.ForeignKey(InformationPackage, null=False, related_name='access_queues')
    new_ip = models.ForeignKey(InformationPackage, null=True, related_name='access_queues_new_ip')
    status = models.IntegerField(null=True, blank=True, default=0, choices=req_status_CHOICES)
    path = models.CharField(max_length=255)
    posted = models.DateTimeField(auto_now_add=True)

    class Meta:
        get_latest_by = 'posted'
        permissions = (
            ("list_accessqueue", "Can list access queue"),
        )
