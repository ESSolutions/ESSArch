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

import uuid
from copy import copy

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from picklefield.fields import PickledObjectField

from ESSArch_Core.profiles.utils import (
    fill_specification_data,
    lowercase_profile_types,
    profile_types,
)
from ESSArch_Core.profiles.validators import validate_template

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


class ProfileSA(models.Model):
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
        settings.AUTH_USER_MODEL, models.SET_NULL, null=True, blank=True,
    )
    Unlockable = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)

    class Meta:
        unique_together = (
            ("profile", "submission_agreement"),
        )


class ProfileIP(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    profile = models.ForeignKey(
        'Profile', on_delete=models.CASCADE
    )
    ip = models.ForeignKey(
        'ip.InformationPackage', on_delete=models.CASCADE
    )
    data = models.ForeignKey('ProfileIPData', on_delete=models.SET_NULL, null=True)
    included = models.BooleanField(default=False)
    LockedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.SET_NULL, null=True, blank=True
    )
    Unlockable = models.BooleanField(default=False)

    def clean(self):
        data = getattr(self.data, 'data', {})
        data = fill_specification_data(data.copy(), ip=self.ip, sa=self.ip.submission_agreement)
        validate_template(self.profile.template, data)

    def lock(self, user):
        self.LockedBy = user

        # extra_data = fill_specification_data(ip=self.ip, sa=self.ip.submission_agreement)
        # for field in self.profile.template:
        #     if 'defaultValue' in field and field['key'] not in self.profile.specification_data.keys():
        #         if field['defaultValue'] in extra_data:
        #             self.profile.specification_data[field['key']] = extra_data[field['defaultValue']]
        #             continue
        #
        #         self.profile.specification_data[field['key']] = field['defaultValue']
        #
        # self.profile.save(update_fields=['specification_data'])
        self.save(update_fields=['LockedBy'])

    def get_related_profile_data(self, original_keys=False):
        data = {}
        for field in self.profile.template:
            if field['key'].startswith('$'):
                profile_type, key = field['key'].split('__')
                profile_type = profile_type[1:]

                try:
                    related_profile = ProfileIP.objects.get(ip=self.ip, profile__profile_type=profile_type)
                except ProfileIP.DoesNotExist:
                    continue
                if related_profile.data is not None:
                    data[field['key'] if original_keys else key] = related_profile.data.data.get(key)

        return data

    def __str__(self):
        return str(self.id)

    class Meta:
        unique_together = (
            ("profile", "ip"),
        )


class ProfileIPData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relation = models.ForeignKey('ProfileIP', on_delete=models.CASCADE, related_name='data_versions')
    data = models.JSONField(default=dict)
    version = models.IntegerField(default=0)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    parsed_files = PickledObjectField(default=list)
    extra_paths_to_parse = PickledObjectField(default=list)

    class Meta:
        ordering = ['version']
        permissions = (
            ('profile_management', 'Can manage profiles'),
        )


class ProfileIPDataTemplate(models.Model):
    name = models.CharField(max_length=50, blank=False)
    data = models.JSONField(default=dict)
    created = models.DateTimeField(auto_now_add=True)
    profile = models.ForeignKey('Profile', on_delete=models.CASCADE)

    class Meta:
        ordering = ['created']


class SubmissionAgreement(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
    )

    name = models.CharField(max_length=255)
    published = models.BooleanField(default=False)
    type = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    label = models.CharField(max_length=255)
    overall_submission_agreement = models.CharField(blank=True, max_length=255)
    archivist_organization = models.CharField(blank=True, max_length=255)
    policy = models.ForeignKey(
        'configuration.StoragePolicy',
        on_delete=models.PROTECT,
        verbose_name="storage policy",
        related_name='submission_agreements',
        null=True,
    )
    include_profile_transfer_project = models.BooleanField(default=False)
    include_profile_content_type = models.BooleanField(default=False)
    include_profile_data_selection = models.BooleanField(default=False)
    include_profile_authority_information = models.BooleanField(default=False)
    include_profile_archival_description = models.BooleanField(default=False)
    include_profile_import = models.BooleanField(default=False)
    include_profile_submit_description = models.BooleanField(default=False)
    include_profile_sip = models.BooleanField(default=False)
    include_profile_aip = models.BooleanField(default=False)
    include_profile_dip = models.BooleanField(default=False)
    include_profile_workflow = models.BooleanField(default=False)
    include_profile_preservation_metadata = models.BooleanField(default=False)
    include_profile_event = models.BooleanField(default=False)

    profile_transfer_project = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='transfer_project_sa'
    )
    profile_content_type = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='content_type_sa'
    )
    profile_data_selection = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='data_selection_sa'
    )
    profile_authority_information = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='authority_information_sa'
    )
    profile_archival_description = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='archival_description_sa'
    )
    profile_import = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='import_sa'
    )
    profile_submit_description = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='submit_description_sa'
    )
    profile_sip = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='sip_sa'
    )
    profile_aic_description = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='aic_description_sa'
    )
    profile_aip = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='aip_sa'
    )
    profile_dip = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='dip_sa'
    )
    profile_aip_description = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='aip_description_sa'
    )
    profile_workflow = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='workflow_sa'
    )
    profile_preservation_metadata = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='preservation_metadata_sa'
    )
    profile_event = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='event_sa'
    )
    profile_validation = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='validation_sa'
    )
    profile_action_workflow = models.ForeignKey(
        'profiles.Profile', on_delete=models.SET_NULL, null=True, related_name='action_workflow_sa'
    )

    template = models.JSONField(default=list)

    class Meta:
        ordering = ["name"]
        verbose_name = _('submission agreement')
        verbose_name_plural = _('submission agreements')
        permissions = (
            ('create_new_sa_generation', 'Can create new generations of SA'),
            ('export_sa', 'Can export SA'),
        )

    def __str__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.name, self.id)

    def get_profiles(self):
        return [getattr(self, 'profile_%s' % p_type, None) for p_type in lowercase_profile_types]

    def get_profile_rel(self, profile_type):
        return self.profilesa_set.filter(
            profile__profile_type=profile_type
        ).first()

    def get_profile(self, profile_type):
        rel = self.get_profile_rel(profile_type)

        if rel:
            return rel.profile

        return None

    def get_archivist_organization_agent(self):
        from ESSArch_Core.ip.models import Agent
        if self.archivist_organization:
            try:
                ao_agent = Agent.objects.get(
                    role='ARCHIVIST', type='ORGANIZATION',
                    name=self.archivist_organization
                )
                return ao_agent
            except Agent.DoesNotExist:
                return None
        return None

    def lock_to_information_package(self, ip, user):
        from ESSArch_Core.ip.models import Agent

        ip.submission_agreement_locked = True

        if ip.submission_agreement_data is not None:
            ip.submission_agreement_data.clean()

        if self.archivist_organization:
            # existing_agents_with_notes = Agent.objects.all().with_notes([])
            ao_agent, _ = Agent.objects.get_or_create(
                role='ARCHIVIST', type='ORGANIZATION',
                name=self.archivist_organization,  # pk__in=existing_agents_with_notes
            )
            ip.agents.add(ao_agent)
        ip.save()
        ip.create_profile_rels(lowercase_profile_types, user)

    def copy(self, new_data, new_name):
        """
        Copies the SA and updates the name and data of the
        copy.

        Args:
            new_data: The data to be used in the copy
            new_name: The name of the copy
        Returns:
            The copy
        """

        clone = copy(self)
        clone.pk = None
        clone.name = new_name

        for k, v in new_data.items():
            setattr(clone, k, v)

        clone.save()

        for profile_sa in ProfileSA.objects.filter(submission_agreement_id=self).iterator(chunk_size=1000):
            ProfileSA.objects.create(submission_agreement=clone, profile=profile_sa.profile)

        return clone


class SubmissionAgreementIPData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission_agreement = models.ForeignKey('profiles.SubmissionAgreement', on_delete=models.CASCADE)
    information_package = models.ForeignKey('ip.InformationPackage', on_delete=models.CASCADE)
    data = models.JSONField(default=dict)
    version = models.IntegerField(default=0)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            ('submission_agreement', 'information_package', 'version'),
        )
        ordering = ['version']

    def clean(self):
        data = self.data or {}
        data = fill_specification_data(data.copy(), ip=self.information_package, sa=self.submission_agreement)
        validate_template(self.submission_agreement.template, data)


PROFILE_TYPE_CHOICES = zip(
    lowercase_profile_types,
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
    type = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=255, blank=True)
    label = models.CharField(max_length=255, blank=True)
    cm_version = models.CharField(max_length=255, blank=True)
    cm_release_date = models.CharField(max_length=255, blank=True)
    cm_change_authority = models.CharField(max_length=255, blank=True)
    cm_change_description = models.CharField(max_length=255, blank=True)
    cm_sections_affected = models.CharField(max_length=255, blank=True)
    schemas = models.JSONField(default=dict)
    representation_info = models.CharField(max_length=255, blank=True)
    preservation_descriptive_info = models.CharField(max_length=255, blank=True)
    supplemental = models.CharField(max_length=255, blank=True)
    access_constraints = models.CharField(max_length=255, blank=True)
    datamodel_reference = models.CharField(max_length=255, blank=True)
    additional = models.CharField(max_length=255, blank=True)
    submission_method = models.CharField(max_length=255, blank=True)
    submission_schedule = models.CharField(max_length=255, blank=True)
    submission_data_inventory = models.CharField(max_length=255, blank=True)
    structure = models.JSONField(default=list, blank=True)
    template = models.JSONField(default=list, blank=True)
    specification = models.JSONField(default=dict, blank=True)
    specification_data = models.JSONField(default=dict, blank=True)

    def get_value_for_key(self, key):
        return self.specification_data.get(key)

    class Meta:
        ordering = ["name"]
        verbose_name = _('profile')
        verbose_name_plural = _('profiles')
        permissions = (
            ('export_profile', 'Can export profile'),
        )

    def __str__(self):
        return '%s (%s) - %s' % (self.name, self.profile_type, self.id)

    def copy(self, specification_data, new_name, structure=None):
        """
        Copies the profile and updates the name and specification_data of the
        copy.

        Args:
            specification_data: The data to be used in the copy
            new_name: The name of the new profile
            structure: The structure of the new profile
        Returns:
            The new profile
        """

        if structure is None:
            structure = {}

        copy = Profile.objects.get(pk=self.pk)
        copy.id = None
        copy.name = new_name
        copy.specification_data = specification_data
        copy.structure = structure
        copy.clean()
        copy.save()

        return copy

    def get_value_array(self):
        # make an associative array of all fields  mapping the field
        # name to the current value of the field
        return {field.name: field.value_to_string(self)
                for field in Profile._meta.fields}
