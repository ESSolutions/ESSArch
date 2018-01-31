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

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import models

import uuid


class CachedManagerMixin:
    def cached(self, search_key, search_value, value_column):
        model_name = self.model.__class__.__name__.lower()

        cache_name = '%s_%s' % (model_name, search_value)
        val = cache.get(cache_name)

        if val is None:
            val = self.model.objects.values_list(value_column, flat=True).get(**{search_key: search_value})
            cache.set(cache_name, val, 3600*24)

        return val


class ParameterManager(models.Manager, CachedManagerMixin):
    pass


class Parameter(models.Model):
    """
    Parameters for configuration options
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.CharField(max_length=60, unique=True)
    value = models.CharField(max_length=70)

    objects = ParameterManager()

    class Meta:
        ordering = ["entity"]
        verbose_name = 'Parameter'

    def __unicode__(self):
        # create a unicode representation of this object
        return self.entity

    def get_value_array(self):
        # make an associative array of all fields  mapping the field
        # name to the current value of the field
        return {
            field.name: field.value_to_string(self)
            for field in Parameter._meta.fields
        }


class PathManager(models.Manager, CachedManagerMixin):
    pass


class Path(models.Model):
    """
    Paths used for different operations
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.CharField(max_length=255, unique=True)
    value = models.CharField(max_length=255)

    objects = PathManager()

    def __unicode__(self):
        return '%s (%s)' % (self.entity, self.value)

    class Meta:
        ordering = ["entity"]
        verbose_name = 'Path'


class EventType(models.Model):
    """
    EventType
    """
    eventType = models.IntegerField(primary_key=True, default=0)
    eventDetail = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
    code = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ["eventType"]
        verbose_name = 'Event Type'

    def __unicode__(self):
        # create a unicode representation of this object
        return self.eventDetail

    def populate_from_form(self, form):
        # pull out all fields from a form and use them to set
        # the values of this object.
        for field in EventType._meta.fields:
            if field.name in form.cleaned_data:
                setattr(self, field.name, form.cleaned_data[field.name])

    def get_value_array(self):
        # make an associative array of all fields  mapping the field
        # name to the current value of the field
        return {
            field.name: field.value_to_string(self)
            for field in EventType._meta.fields
        }


class Agent(models.Model):
    """
    Agents used for different operations
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agentType = models.CharField(max_length=60, unique=True)
    agentDetail = models.CharField(max_length=70)

    class Meta:
        ordering = ["agentType"]
        verbose_name = 'Agent'


class DefaultColumnVisible(models.Model):
    """Specifies if a column should be visible to a user by default"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    field = models.CharField(max_length=255)
    visible = models.BooleanField(default=True)


class ArchivePolicy(models.Model):
    """Specifies how an IP should be archived"""

    MODE_CHOICES = (
        (0, 'master'),
        (2, 'ais'),
    )

    MD5 = 0
    SHA1 = 1
    SHA224 = 2
    SHA256 = 3
    SHA384 = 4
    SHA512 = 5

    CHECKSUM_ALGORITHM_CHOICES = (
        (MD5, 'md5'),
        (SHA1, 'sha-1'),
        (SHA224, 'sha-224'),
        (SHA256, 'sha-256'),
        (SHA384, 'sha-384'),
        (SHA512, 'sha-512'),
    )

    IP_TYPE_CHOICES = (
        (1, 'tar'),
    )

    PREINGEST_METADATA_CHOICES = (
        (0, 'disabled'),
        (1, 'res'),
    )

    INGEST_METADATA_CHOICES = (
        (1, 'mets'),
        (4, 'mets (eard)'),
    )

    INFORMATION_CLASS_CHOICES = (
        (0, '0'),
        (1, '1'),
        (2, '2'),
        (3, '3'),
        (4, '4'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    index = models.BooleanField(default=True)

    cache_extracted_size = models.BigIntegerField('Maximum size (bytes) of extracted package before deletion from cache', null=True)
    cache_package_size = models.BigIntegerField('Maximum size (bytes) of package before deletion from cache', null=True)
    cache_extracted_age = models.IntegerField('Maximum age (days) of extracted package before deletion from cache', null=True)
    cache_package_age = models.IntegerField('Maximum age (days) of package before deletion from cache', null=True)

    policy_id = models.CharField('Policy ID', max_length=32, unique=True)
    policy_name = models.CharField('Policy Name', max_length=255)
    policy_stat = models.BooleanField('Policy Status', default=False)
    ais_project_name = models.CharField('AIS Policy Name', max_length=255, blank=True)
    ais_project_id = models.CharField('AIS Policy ID', max_length=255, blank=True)
    mode = models.IntegerField(choices=MODE_CHOICES, default=0)
    wait_for_approval = models.BooleanField('Wait for approval', default=True)
    checksum_algorithm = models.IntegerField('Checksum algorithm', choices=CHECKSUM_ALGORITHM_CHOICES, default=1)
    validate_checksum = models.BooleanField('Validate checksum', default=True)
    validate_xml = models.BooleanField('Validate XML', default=True)
    ip_type = models.IntegerField('IP type', choices=IP_TYPE_CHOICES, default=1)
    cache_storage = models.ForeignKey(Path, on_delete=models.PROTECT, related_name='cache_policy')
    preingest_metadata = models.IntegerField('Pre ingest metadata', choices=PREINGEST_METADATA_CHOICES, default=0)
    ingest_metadata = models.IntegerField('Ingest metadata', choices=INGEST_METADATA_CHOICES, default=4)
    information_class = models.IntegerField('Information class', choices=INFORMATION_CLASS_CHOICES, default=0)
    ingest_path = models.ForeignKey(Path, on_delete=models.PROTECT, related_name='ingest_policy')
    ingest_delete = models.BooleanField('Delete SIP after success to create AIP', default=True)
    receive_extract_sip = models.BooleanField('Extract SIP on receive', default=False)


    class Meta:
        ordering = ['policy_name']

    def __unicode__(self):
        if len(self.policy_name):
            return self.policy_name
        elif len(self.policy_id):
            return unicode(self.policy_id)
        else:
            return str(self.pk)


class DefaultSorting(models.Model):
    """Specifies the default sorting field for a user"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    field = models.CharField(max_length=255)
    descending = models.BooleanField(default=True)


class DefaultValue(models.Model):
    """Specifies the default values for fields for a user"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    field = models.CharField(max_length=255)
    value = models.CharField(max_length=255, blank=True)
