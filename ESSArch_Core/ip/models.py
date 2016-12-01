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

# Create your models here.
from __future__ import division

from _version import get_versions

from celery import states as celery_states

from collections import OrderedDict

from django.conf import settings
from django.db import models

from ESSArch_Core.configuration.models import (
    EventType, Path,
)

from ESSArch_Core.WorkflowEngine.models import (
    ProcessStep, ProcessTask,
)

from ESSArch_Core.profiles.models import (
    SubmissionAgreement as SA,
    ProfileIP, ProfileSA,
)

from ESSArch_Core.util import (
    create_event,
    creation_date,
    get_tree_size_and_count,
    timestamp_to_datetime,
)

from ESSArch_Core.essxml.Generator.xmlGenerator import (
    downloadSchemas, find_destination
)

from scandir import scandir, walk

import hashlib, json, math, os, uuid


class ArchivalInstitution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'ArchivalInstitution'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.name, self.id)


class ArchivistOrganization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'ArchivistOrganization'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.name, self.id)


class ArchivalType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'ArchivalType'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.name, self.id)


class ArchivalLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'ArchivalLocation'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.name, self.id)


class InformationPackage(models.Model):
    """
    Informaion Package
    """

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    ObjectIdentifierValue = models.CharField(max_length=255, null=True)
    Label = models.CharField(max_length=255)
    Content = models.CharField(max_length=255)
    Responsible = models.CharField(max_length=255)
    CreateDate = models.DateTimeField(auto_now_add=True)
    State = models.CharField(max_length=255)
    ObjectPath = models.CharField(max_length=255)
    Startdate = models.DateTimeField(null=True)
    Enddate = models.DateTimeField(null=True)
    OAIStype = models.CharField(max_length=255)
    SubmissionAgreement = models.ForeignKey(
        SA,
        on_delete=models.CASCADE,
        related_name='information_packages',
        default=None,
        null=True,
    )
    SubmissionAgreementLocked = models.BooleanField(default=False)
    ArchivalInstitution = models.ForeignKey(
        ArchivalInstitution,
        on_delete=models.CASCADE,
        related_name='information_packages',
        default=None,
        null=True
    )
    ArchivistOrganization = models.ForeignKey(
        ArchivistOrganization,
        on_delete=models.CASCADE,
        related_name='information_packages',
        default=None,
        null=True
    )
    ArchivalType = models.ForeignKey(
        ArchivalType,
        on_delete=models.CASCADE,
        related_name='information_packages',
        default=None,
        null=True
    )
    ArchivalLocation = models.ForeignKey(
        ArchivalLocation,
        on_delete=models.CASCADE,
        related_name='information_packages',
        default=None,
        null=True
    )

    def save(self, *args, **kwargs):
        super(InformationPackage, self).save(*args, **kwargs)

        if not self.ObjectIdentifierValue:
            self.ObjectIdentifierValue = str(self.pk)
            self.save()

    @property
    def ObjectSizeAndNum(self):
        return get_tree_size_and_count(self.ObjectPath)

    def get_profile_rel(self, profile_type):
        return self.profileip_set.filter(
            profile__profile_type=profile_type
        ).first()

    def profile_locked(self, profile_type):
        rel = self.get_profile_rel(profile_type)

        if rel:
            return rel.LockedBy is not None

        return False

    def get_profile(self, profile_type):
        rel = self.get_profile_rel(profile_type)

        if rel:
            return rel.profile

        return None

    def change_profile(self, new_profile):
        ptype = new_profile.profile_type
        try:
            pip = ProfileIP.objects.get(ip=self, profile__profile_type=ptype)
            pip.profile = new_profile
            pip.save()
        except ProfileIP.DoesNotExist:
            ProfileIP.objects.create(ip=self, profile=new_profile)

    def unlock_profile(self, ptype):
        ProfileIP.objects.filter(
            ip=self, profile__profile_type=ptype
        ).delete()

    def get_container_format(self):
        try:
            return self.get_profile('transfer_project').specification_data.get(
                'container_format', 'tar'
            )
        except:
            return 'tar'

    def get_checksum_algorithm(self):
        try:
            name = self.get_profile('transfer_project').specification_data.get(
                'checksum_algorithm', 'sha256'
            )
        except:
            name = 'sha256'

        return name

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
        if self.State in ["Prepared", "Created", "Submitted", "Received", "Transferred"]:
            return 100

        if self.State == "Preparing":
            if self.SubmissionAgreementLocked:
                return 100

            progress = 33

            try:
                sa_profiles = ProfileSA.objects.filter(
                    submission_agreement=self.SubmissionAgreement
                )

                ip_profiles_locked = ProfileIP.objects.filter(
                    ip=self, LockedBy__isnull=False,
                    profile__profile_type__in=sa_profiles.values(
                        "profile__profile_type"
                    )
                )

                progress += math.ceil(ip_profiles_locked.count() * (33 / sa_profiles.count()))

            except ZeroDivisionError:
                pass

            return progress

        if self.State in ["Creating", "Submitting", "Receiving", "Transferring"]:
            steps = self.steps.all()

            if steps:
                try:
                    progress = sum([s.progress() for s in steps])
                    return progress / len(steps)
                except:
                    return 0

            return 0

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

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.Label, self.pk)

    def get_value_array(self):
        # make an associative array of all fields  mapping the field
        # name to the current value of the field
        return {
            field.name: field.value_to_string(self)
            for field in InformationPackage._meta.fields
        }


class EventIP(models.Model):
    """
    Events related to IP
    """

    OUTCOME_CHOICES = (
        (0, 'Success'),
        (1, 'Fail')
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    eventType = models.ForeignKey(
        'configuration.EventType',
        on_delete=models.CASCADE
    )
    eventDateTime = models.DateTimeField(auto_now_add=True)
    eventApplication = models.ForeignKey(
        'WorkflowEngine.ProcessTask', on_delete=models.CASCADE, null=True
    ) # The task that generated the event
    eventVersion = models.CharField(max_length=255) # The version number of the application (from versioneer)
    eventOutcome = models.IntegerField(choices=OUTCOME_CHOICES, null=True, default=None) # Success (0) or Fail (1)
    eventOutcomeDetailNote = models.CharField(max_length=1024) # Result or traceback from IP
    linkingAgentIdentifierValue = models.CharField(max_length=255)
    linkingObjectIdentifierValue = models.ForeignKey(
        'InformationPackage',
        on_delete=models.CASCADE,
        related_name='events',
        null=True,
    )

    def getEventOutcomeDetailNote(self):
        max_len = 1024
        task = self.eventApplication

        if task and task.status == celery_states.FAILURE:
            prefix = "%s (%s) failed: " % (task.name, task.pk)
            exception = task.exception

            total_len = len(prefix) + len(exception)

            if total_len > max_len:
                suffix = ' (truncated)'
                return (prefix + exception)[:max_len - len(suffix)] + suffix

            return prefix + exception

        return self.eventOutcomeDetailNote

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
