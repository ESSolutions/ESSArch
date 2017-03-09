from __future__ import unicode_literals

import uuid

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from picklefield.fields import PickledObjectField

from ESSArch_Core.ip.models import InformationPackage

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
    (200, 'DISK'),
    (300, 'TAPE'),
    (400, 'CAS'),
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


class StorageMethod(models.Model):
    """Disk, tape or CAS"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('Name', max_length=255, blank=True)
    status = models.BooleanField('Storage method status', default=False)
    type = models.IntegerField('Type', choices=storage_type_CHOICES, default=200)
    archive_policy = models.ForeignKey('configuration.ArchivePolicy')
    targets = models.ManyToManyField('StorageTarget', through='StorageMethodTargetRelation', related_name='methods')

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
    storage_target = models.ForeignKey('StorageTarget')
    storage_method = models.ForeignKey('StorageMethod')

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

    class Meta:
        verbose_name = 'Storage Target'
        ordering = ['name']

    def __unicode__(self):
        if len(self.name):
            return self.name

        return unicode(self.id)


class StorageMedium(models.Model):
    "A single storage medium (device)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    medium_id = models.CharField("The id for the medium, e.g. barcode", max_length=255, unique=True)
    status = models.IntegerField(choices=medium_status_CHOICES)
    location = models.CharField(max_length=255)
    location_status = models.IntegerField(choices=medium_location_status_CHOICES)
    block_size = models.IntegerField(choices=medium_block_size_CHOICES)
    format = models.IntegerField(choices=medium_format_CHOICES)
    used_capacity = models.BigIntegerField()
    number_of_mounts = models.IntegerField()

    create_date = models.DateTimeField(auto_now_add=True)
    last_changed_local = models.DateTimeField(null=True)
    last_changed_external = models.DateTimeField(null=True)

    agent = models.ForeignKey('auth.User', on_delete=models.PROTECT)
    storage_target = models.ForeignKey('StorageTarget')

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


class StorageObject(models.Model):
    """The stored representation of an archive object on a storage medium"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_location_type = models.IntegerField(choices=storage_type_CHOICES)
    content_location_value = models.CharField(max_length=255)

    last_changed_local = models.DateTimeField(null=True)
    last_changed_external = models.DateTimeField(null=True)

    ip = models.ForeignKey(InformationPackage, related_name='storage')
    storage_medium = models.ForeignKey('StorageMedium', related_name='storage')

    class Meta:
        permissions = (
            ("list_storage", "Can list storage"),
        )

    def __unicode__(self):
        try:
            medium_id = self.storage_medium.medium_id
        except ObjectDoesNotExist:
            medium_id = 'unknown media'

        try:
            obj_identifier_value = self.ip.ObjectIdentifierValue
        except ObjectDoesNotExist:
            obj_identifier_value = 'unknown object'

        return '%s @ %s' % (obj_identifier_value, medium_id)

    def check_db_sync(self):
        if self.last_changed_local is not None and self.last_changed_external is not None:
            return (self.last_changed_local-self.last_changed_external).total_seconds() == 0

        return False


class IOQueue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    req_type = models.IntegerField(choices=IOReqType_CHOICES)
    req_purpose = models.CharField(max_length=255, blank=True)
    user = models.CharField(max_length=45)
    object_path = models.CharField(max_length=256, blank=True)
    write_size = models.BigIntegerField(null=True, blank=True)
    result = PickledObjectField(blank=True)
    status = models.IntegerField(blank=True, default=0, choices=req_status_CHOICES)
    task_id = models.CharField(max_length=36, blank=True)
    posted = models.DateTimeField(auto_now_add=True)
    ip = models.ForeignKey(InformationPackage, null=True)
    storage_method = models.ForeignKey('StorageMethod', blank=True, null=True)
    storage_method_target = models.ForeignKey('StorageMethodTargetRelation', blank=True, null=True)
    storage_target = models.ForeignKey('StorageTarget', blank=True, null=True)
    storage_medium = models.ForeignKey('StorageMedium', blank=True, null=True)
    storage_object = models.ForeignKey('StorageObject', blank=True, null=True)
    access_queue = models.ForeignKey('AccessQueue', blank=True, null=True)
    remote_status = models.IntegerField(blank=True, default=0, choices=remote_status_CHOICES)
    transfer_task_id = models.CharField(max_length=36, blank=True)

    class Meta:
        permissions = (
            ("list_IOQueue", "Can list IOQueue"),
        )


class AccessQueue(models.Model):
    ACCESS_REQ_TYPE_CHOICES = (
        (3, 'Generate DIP (package)'),
        (4, 'Generate DIP (package extracted)'),
        (1, 'Generate DIP (package & package extracted)'),
        (2, 'Verify StorageMedium'),
        (5, 'Get AIP to ControlArea'),
    )

    REQ_STATUS_CHOICES = (
        (0, 'Pending'),
        (2, 'Initiate'),
        (5, 'Progress'),
        (20, 'Success'),
        (100, 'FAIL'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    req_uuid = models.CharField(max_length=36)
    req_type = models.IntegerField(null=True, choices=ACCESS_REQ_TYPE_CHOICES)
    req_purpose = models.CharField(max_length=255)
    user = models.CharField(max_length=45)
    password = models.CharField(max_length=45, blank=True)
    object_identifier_value = models.CharField(max_length=255, blank=True)
    storage_medium_id = models.CharField(max_length=45, blank=True)
    status = models.IntegerField(null=True, blank=True, default=0, choices=REQ_STATUS_CHOICES)
    path = models.CharField(max_length=255)
    posted = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = (
            ("list_accessqueue", "Can list access queue"),
        )
