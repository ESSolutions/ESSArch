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
from django.core.exceptions import ValidationError
from django.db import models

import jsonfield
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
        User, models.SET_NULL, null=True, blank=True,
    )
    Unlockable = models.BooleanField(default=False)

    def __unicode__(self):
        return unicode(self.id)

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
    included = models.BooleanField(default=False)
    LockedBy = models.ForeignKey(
        User, models.SET_NULL, null=True, blank=True
    )
    Unlockable = models.BooleanField(default=False)

    def lock(self, user):
        self.LockedBy = user
        self.save()

    def __unicode__(self):
        return unicode(self.id)

    class Meta:
        unique_together = (
            ("profile", "ip"),
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

    class Meta:
        ordering = ["sa_name"]
        verbose_name = 'Submission Agreement'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s - %s' % (self.sa_name, self.id)

    def get_profile_rel(self, profile_type):
        return self.profilesa_set.filter(
            profile__profile_type=profile_type
        ).first()

    def get_profile(self, profile_type):
        rel = self.get_profile_rel(profile_type)

        if rel:
            return rel.profile

        return None


profile_types = [
    "Transfer Project",
    "Content Type",
    "Data Selection",
    "Authority Information",
    "Archival Description",
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

    def fill_specification_data(self, sa=None, ip=None):
        data = self.specification_data

        if sa:
            data['_SA_ID'] = str(sa.pk)
            data['_SA_NAME'] = str(sa.sa_name)

        if ip:
            data['_OBJID'] = str(ip.pk)
            data['_OBJLABEL'] = ip.Label

            if ip.ArchivistOrganization:
                data['_IP_ARCHIVIST_ORGANIZATION'] = ip.ArchivistOrganization.name

            if ip.ArchivalInstitution:
                data['_IP_ARCHIVAL_INSTITUTION'] = ip.ArchivalInstitution.name

            if ip.ArchivalType:
                data['_IP_ARCHIVAL_TYPE'] = ip.ArchivalType.name

            if ip.ArchivalLocation:
                data['_IP_ARCHIVAL_LOCATION'] = ip.ArchivalLocation.name

            try:
                data["_PROFILE_TRANSFER_PROJECT_ID"] = str(ip.get_profile('transfer_project').pk)
            except AttributeError:
                pass

            try:
                data["_PROFILE_SUBMIT_DESCRIPTION_ID"] = str(ip.get_profile('submit_description').pk)
            except AttributeError:
                pass

            try:
                data["_PROFILE_SIP_ID"] = str(ip.get_profile('sip').pk)
            except AttributeError:
                pass

            try:
                data["_PROFILE_AIP_ID"] = str(ip.get_profile('aip').pk)
            except AttributeError:
                pass

            try:
                data["_PROFILE_DIP_ID"] = str(ip.get_profile('dip').pk)
            except AttributeError:
                pass

            try:
                data["_PROFILE_CONTENT_TYPE_ID"] = str(ip.get_profile('content_type').pk)
            except AttributeError:
                pass

            try:
                data["_PROFILE_AUTHORITY_INFORMATION_ID"] = str(ip.get_profile('authority_information').pk)
            except AttributeError:
                pass

            try:
                data["_PROFILE_ARCHIVAL_DESCRIPTION_ID"] = str(ip.get_profile('archival_description').pk)
            except AttributeError:
                pass

            try:
                data["_PROFILE_PRESERVATION_METADATA_ID"] = str(ip.get_profile('preservation_metadata').pk)
            except AttributeError:
                pass

            try:
                data["_PROFILE_DATA_SELECTION_ID"] = str(ip.get_profile('data_selection').pk)
            except AttributeError:
                pass

            try:
                data["_PROFILE_IMPORT_ID"] = str(ip.get_profile('import').pk)
            except AttributeError:
                pass

            try:
                data["_PROFILE_WORKFLOW_ID"] = str(ip.get_profile('workflow').pk)
            except AttributeError:
                pass

        return data

    def clean(self):
        for field in self.template:
            if field.get('templateOptions', {}).get('required') and not self.specification_data.get(field.get('key')):
                raise ValidationError("Required field (%s) can't be empty" % (field.get('key')))

    class Meta:
        ordering = ["name"]
        verbose_name = 'Profile'

    def __unicode__(self):
        # create a unicode representation of this object
        return '%s (%s) - %s' % (self.name, self.profile_type, self.id)

    def copy_and_switch(self, ip, specification_data, new_name, structure={}):
        """
        Copies the profile and updates the name and specification_data of the
        copy. Switches the relation from the ip with the old profile to the new
        profile

        Args:
            ip: The information package that the profile is
                                  switched in
            specification_data: The data to be used in the copy
            new_name: The name of the new profile
        Returns:
            None
        """

        copy = Profile.objects.get(pk=self.pk)
        copy.id = None
        copy.name = new_name
        copy.specification_data = specification_data
        copy.structure = structure
        copy.save()

        ip.change_profile(copy)
        return copy

    def get_value_array(self):
        # make an associative array of all fields  mapping the field
        # name to the current value of the field
        return {field.name: field.value_to_string(self)
                for field in Profile._meta.fields}
