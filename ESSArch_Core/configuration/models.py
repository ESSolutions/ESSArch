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

"""
    ESSArch Tools - ESSArch is an Electronic Preservation Platform
    Copyright (C) 2005-2016  ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

from django.db import models

import uuid


class Parameter(models.Model):
    """
    Parameters for configuration options
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.CharField(max_length=60, unique=True)
    value = models.CharField(max_length=70)

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


class Path(models.Model):
    """
    Paths used for different operations
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.CharField(max_length=60, unique=True)
    value = models.CharField(max_length=70)

    class Meta:
        ordering = ["entity"]
        verbose_name = 'Path'


class EventType(models.Model):
    """
    EventType
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    eventType = models.IntegerField(default=0, unique=True)
    eventDetail = models.CharField(max_length=255)

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
