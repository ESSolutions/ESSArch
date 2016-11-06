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

from django.contrib.auth.models import User
from django.db import models

from ESSArch_Core.configuration.models import (
    Path
)

from ESSArch_Core.WorkflowEngine.models import (
    ProcessStep, ProcessTask,
)

import jsonfield
import os
import uuid

Profile_Status_CHOICES = (
    (0, 'Disabled'),
    (1, 'Enabled'),
    (2, 'Default'),
)


class ProfileQuerySet(models.query.QuerySet):
    def active(self):
        """
        Gets the first profile in the base set that have status 1 (enabled), if
        there is none get the first profile with status 2 (default)

        Args:

        Returns:
            The first profile with status 1 if there is one,
            otherwise the first profile with status 2
        """

        profile_set = self.filter(
            status=1
        )

        if not profile_set:
            profile_set = self.filter(
                status=2
            )

        if not profile_set:
            return None

        return profile_set.first().profile


class ProfileRelManager(models.Manager):
    def get_queryset(self):
        return ProfileQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()


class ProfileRel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.IntegerField(
        'Profile status',
        choices=Profile_Status_CHOICES,
        default=0
    )
    profile = models.ForeignKey('Profile')
    submission_agreement = models.ForeignKey('SubmissionAgreement')
    objects = ProfileRelManager()

    class Meta:
        base_manager_name = 'objects'
        verbose_name = 'ProfileRel'
        ordering = ['status']

    def __unicode__(self):
        return unicode(self.id)


class ProfileSALock(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    profile = models.ForeignKey(
        'Profile', on_delete=models.CASCADE
    )
    submission_agreement = models.ForeignKey(
        'SubmissionAgreement', on_delete=models.CASCADE
    )
    LockedBy = models.ForeignKey(
        User, models.SET_NULL, null=True,
    )
    Unlockable = models.BooleanField(default=False)

    def __unicode__(self):
        return unicode(self.id)

    class Meta:
        unique_together = (
            ("profile", "submission_agreement"),
        )

class SAIPLock(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    submission_agreement = models.ForeignKey(
        'SubmissionAgreement', on_delete=models.CASCADE
    )
    information_package = models.ForeignKey(
        'ip.InformationPackage', on_delete=models.CASCADE
    )
    LockedBy = models.ForeignKey(
        User, models.SET_NULL, null=True,
    )
    Unlockable = models.BooleanField(default=False)

    def __unicode__(self):
        return unicode(self.id)

    class Meta:
        unique_together = (
            ("submission_agreement", "information_package"),
        )

class SubmissionAgreement(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    sa_name = models.CharField(max_length=255)
    sa_type = models.CharField(max_length=255)
    sa_status = models.CharField(max_length=255)
    sa_label = models.CharField(max_length=255)
    sa_cm_version = models.CharField(max_length=255)
    sa_cm_release_date = models.CharField(max_length=255)
    sa_cm_change_authority = models.CharField(max_length=255)
    sa_cm_change_description = models.CharField(max_length=255)
    sa_cm_sections_affected = models.CharField(max_length=255)
    sa_producer_organization = models.CharField(max_length=255)
    sa_producer_main_name = models.CharField(max_length=255)
    sa_producer_main_address = models.CharField(max_length=255)
    sa_producer_main_phone = models.CharField(max_length=255)
    sa_producer_main_email = models.CharField(max_length=255)
    sa_producer_main_additional = models.CharField(max_length=255)
    sa_producer_individual_name = models.CharField(max_length=255)
    sa_producer_individual_role = models.CharField(max_length=255)
    sa_producer_individual_phone = models.CharField(max_length=255)
    sa_producer_individual_email = models.CharField(max_length=255)
    sa_producer_individual_additional = models.CharField(max_length=255)
    sa_archivist_organization = models.CharField(max_length=255)
    sa_archivist_main_name = models.CharField(max_length=255)
    sa_archivist_main_address = models.CharField(max_length=255)
    sa_archivist_main_phone = models.CharField(max_length=255)
    sa_archivist_main_email = models.CharField(max_length=255)
    sa_archivist_main_additional = models.CharField(max_length=255)
    sa_archivist_individual_name = models.CharField(max_length=255)
    sa_archivist_individual_role = models.CharField(max_length=255)
    sa_archivist_individual_phone = models.CharField(max_length=255)
    sa_archivist_individual_email = models.CharField(max_length=255)
    sa_archivist_individual_additional = models.CharField(max_length=255)
    sa_designated_community_description = models.CharField(max_length=255)
    sa_designated_community_individual_name = models.CharField(max_length=255)
    sa_designated_community_individual_role = models.CharField(max_length=255)
    sa_designated_community_individual_phone = models.CharField(max_length=255)
    sa_designated_community_individual_email = models.CharField(max_length=255)
    sa_designated_community_individual_additional = models.CharField(
        max_length=255
    )

    profiles = models.ManyToManyField(
        'Profile',
        related_name='submission_agreements',
        through='ProfileRel',
        through_fields=('submission_agreement', 'profile')
    )

    include_profile_transfer_project = models.BooleanField(default=False)
    include_profile_content_type = models.BooleanField(default=False)
    include_profile_data_selection = models.BooleanField(default=False)
    include_profile_classification = models.BooleanField(default=False)
    include_profile_import = models.BooleanField(default=False)
    include_profile_submit_description = models.BooleanField(default=False)
    include_profile_sip = models.BooleanField(default=False)
    include_profile_aip = models.BooleanField(default=False)
    include_profile_dip = models.BooleanField(default=False)
    include_profile_workflow = models.BooleanField(default=False)
    include_profile_preservation_metadata = models.BooleanField(default=False)
    include_profile_event = models.BooleanField(default=False)

    @property
    def profile_transfer_project_rel(self):
        return self.profilerel_set.filter(profile__profile_type="transfer_project")

    @property
    def profile_content_type_rel(self):
        return self.profilerel_set.filter(profile__profile_type="content_type")

    @property
    def profile_data_selection_rel(self):
        return self.profilerel_set.filter(profile__profile_type="data_selection")

    @property
    def profile_classification_rel(self):
        return self.profilerel_set.filter(profile__profile_type="classification")

    @property
    def profile_import_rel(self):
        return self.profilerel_set.filter(profile__profile_type="import")

    @property
    def profile_submit_description_rel(self):
        return self.profilerel_set.filter(profile__profile_type="submit_description")

    @property
    def profile_sip_rel(self):
        return self.profilerel_set.filter(profile__profile_type="sip")

    @property
    def profile_aip_rel(self):
        return self.profilerel_set.filter(profile__profile_type="aip")

    @property
    def profile_dip_rel(self):
        return self.profilerel_set.filter(profile__profile_type="dip")

    @property
    def profile_workflow_rel(self):
        return self.profilerel_set.filter(profile__profile_type="workflow")

    @property
    def profile_preservation_metadata_rel(self):
        return self.profilerel_set.filter(profile__profile_type="preservation_metadata")

    @property
    def profile_event_rel(self):
        return self.profilerel_set.filter(profile__profile_type="event")

    class Meta:
        ordering = ["sa_name"]
        verbose_name = 'Submission Agreement'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.sa_name, self.id)

    def change_profile(self, new_profile):
        """
        Sets the given profile as enabled profile of its type in this
        submission agreement.

        Args:
            new_profile: The profile that will be set as enabled for its type

        Returns:
            None
        """

        old_profile = self.profilerel_set.filter(
                profile__profile_type=new_profile.profile_type
        ).active()
        old_status = old_profile.get_sa_status(self)

        if old_status == 1:
            old_profile.set_sa_status(self, 0)

        if new_profile.get_sa_status(self) != 2:
            ProfileRel.objects.update_or_create(
                submission_agreement=self,
                profile=new_profile,
                defaults={
                    "status": 1
                },
            )

    def profile_locks(self):
        return ProfileSALock.objects.filter(
            submission_agreement=self
        )

    def ip_locks(self):
        return SAIPLock.objects.filter(
            submission_agreement=self
        )

    def lock(self, ip):
        """
        Locks the sa in relation to an IP stop further editing
        (if you don't have the permission to unlock it again)

        Args:
            ip: The information package

        Returns:
            The created lock
        """

        return SAIPLock.objects.create(
            submission_agreement=self, information_package=ip
        )

    """
    def get_value_array(self):
        # make an associative array of all fields  mapping the field
        # name to the current value of the field
        return {field.name: field.value_to_string(self)
                for field in SubmissionAgreement._meta.fields}
    """

profile_types = [
    "Transfer Project",
    "Content Type",
    "Data Selection",
    "Classification",
    "Import",
    "Submit Description",
    "SIP",
    "AIP",
    "DIP",
    "Workflow",
    "Preservation Metadata",
    "Event",
]

PROFILE_TYPE_CHOICES = zip(
    [p.replace(' ', '_').lower() for p in profile_types],
    profile_types
)


class Profile(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    profile_type = models.CharField(
        max_length=255,
        choices=PROFILE_TYPE_CHOICES
    )
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    label = models.CharField(max_length=255)
    cm_version = models.CharField(max_length=255)
    cm_release_date = models.CharField(max_length=255)
    cm_change_authority = models.CharField(max_length=255)
    cm_change_description = models.CharField(max_length=255)
    cm_sections_affected = models.CharField(max_length=255)
    schemas = jsonfield.JSONField(null=True)
    representation_info = models.CharField(max_length=255)
    preservation_descriptive_info = models.CharField(max_length=255)
    supplemental = models.CharField(max_length=255)
    access_constraints = models.CharField(max_length=255)
    datamodel_reference = models.CharField(max_length=255)
    additional = models.CharField(max_length=255)
    submission_method = models.CharField(max_length=255)
    submission_schedule = models.CharField(max_length=255)
    submission_data_inventory = models.CharField(max_length=255)
    structure = jsonfield.JSONField(null=True)
    template = jsonfield.JSONField(null=True)
    specification = jsonfield.JSONField(null=True)
    specification_data = jsonfield.JSONField(null=True)

    class Meta:
        ordering = ["name"]
        verbose_name = 'Profile'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s (%s) - %s' % (self.name, self.profile_type, self.id)

    def get_sa_status(self, submission_agreement):
        """
        Gets the status between the profile and the given submission agreement.

        Args:
            submission_agreement: The submission agreement to check the status
                                  with

        Returns:
            The status between the profile and the given submission agreement
        """

        try:
            return self.profilerel_set.get(
                submission_agreement=submission_agreement.pk
            ).status
        except ProfileRel.DoesNotExist:
            return None

    def set_sa_status(self, submission_agreement, status):
        """
        Sets the status between the profile and the given submission agreement.

        Args:
            submission_agreement: The submission agreement which relation
                                  status we will update
            status: The new status

        Returns:
            None
        """

        self.profilerel_set.filter(
            submission_agreement=submission_agreement.pk
        ).update(status=status)

    def copy_and_switch(self, submission_agreement, specification_data, new_name, structure={}):
        """
        Copies the profile and updates the name and specification_data of the
        copy.  If the old profile has a status of 1 (enabled) in it's
        connection to the given submission agreement then the old profile will
        be given the status 0 (disabled). The status of the new profile and the
        submission agreement will always be 1 (enabled).

        Args:
            submission_agreement: The submission agreement that the profile is
                                  switched in
            specification_data: The data to be used in the copy
            new_name: The name of the new profile
        Returns:
            None
        """

        if self.get_sa_status(submission_agreement) == 1:
            self.set_sa_status(submission_agreement, 0)
            self.save()

        copy = Profile.objects.get(pk=self.pk)
        copy.id = None
        copy.name = new_name
        copy.specification_data = specification_data
        copy.structure = structure
        copy.save()

        ProfileRel.objects.create(
            profile=copy, submission_agreement=submission_agreement,
            status=1
        )

    def locked(self, submission_agreement):
        """
        Checks if the profiel is locked to the provided SA

        Args:
            submission_agreement: The submission agreement

        Returns:
            True if locked, false otherwise
        """

        return ProfileSALock.objects.filter(
            profile=self, submission_agreement=submission_agreement,
        ).exists()

    def lock(self, submission_agreement):
        """
        Locks the profile in relation to an SA stop further editing
        (if you don't have the permission to unlock it again)

        Args:
            submission_agreement: The submission agreement

        Returns:
            The created lock
        """

        return ProfileSALock.objects.create(
            profile=self, submission_agreement=submission_agreement,
        )

    def get_value_array(self):
        # make an associative array of all fields  mapping the field
        # name to the current value of the field
        return {field.name: field.value_to_string(self)
                for field in Profile._meta.fields}
