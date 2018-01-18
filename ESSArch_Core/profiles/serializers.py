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

from rest_framework import serializers

from ESSArch_Core.exceptions import Conflict

from ESSArch_Core.ip.models import (
    InformationPackage,
)

from ESSArch_Core.profiles.models import (
    SubmissionAgreement,
    Profile,
    ProfileSA,
    ProfileIP,
    ProfileIPData,
)

from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.profiles.validators import validate_template


class ProfileSASerializer(serializers.ModelSerializer):
    profile_type = serializers.SlugRelatedField(slug_field='profile_type', source='profile', read_only=True)
    profile_name = serializers.SlugRelatedField(slug_field='name', source='profile', read_only=True)
    profile = serializers.PrimaryKeyRelatedField(queryset=Profile.objects.all())

    class Meta:
        model = ProfileSA
        fields = (
            'id', 'profile', 'submission_agreement', 'profile_name', 'profile_type', 'LockedBy', 'Unlockable'
        )


class ProfileIPDataSerializer(serializers.ModelSerializer):
    def validate(self, data):
        relation = data['relation']
        instance_data = data.get('data', {})

        if relation.data is not None and instance_data == relation.data.data:
            raise serializers.ValidationError('No changes made')

        validate_template(relation.profile.template, instance_data)

        return data

    class Meta:
        model = ProfileIPData
        fields = (
            'id', 'relation', 'data', 'version', 'user', 'created',
        )
        extra_kwargs = {
            'user': {
                'read_only': True,
                'default': serializers.CurrentUserDefault(),
            }
        }


class ProfileIPSerializer(serializers.ModelSerializer):
    profile_type = serializers.SlugRelatedField(slug_field='profile_type', source='profile', read_only=True)
    profile_name = serializers.SlugRelatedField(slug_field='name', source='profile', read_only=True)
    data = serializers.SerializerMethodField()

    def get_data(self, obj):
        if obj.data is not None:
            serializer = ProfileIPDataSerializer(obj.data, context={'request': self.context['request']})
            data = serializer.data
        else:
            data = {'data': {}}

        data['data'].update(obj.get_related_profile_data(original_keys=True))
        data['data'] = fill_specification_data(data=data['data'], ip=obj.ip, sa=obj.ip.submission_agreement)
        return data

    class Meta:
        model = ProfileIP
        fields = (
            'id', 'profile', 'ip', 'profile_name', 'profile_type', 'included', 'LockedBy', 'Unlockable', 'data', 'data_versions',
        )
        read_only_fields = (
            'LockedBy',
        )


class ProfileIPWriteSerializer(ProfileIPSerializer):
    data = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=ProfileIPData.objects.all())


class SubmissionAgreementSerializer(serializers.ModelSerializer):
    published = serializers.BooleanField(read_only=True)

    profile_transfer_project = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='transfer_project'))
    profile_content_type = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='content_type'))
    profile_data_selection = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='data_selection'))
    profile_authority_information = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='authority_information'))
    profile_archival_description = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='archival_description'))
    profile_import = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='import'))
    profile_submit_description = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='submit_description'))
    profile_sip = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='sip'))
    profile_aic_description = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='aic_description'))
    profile_aip = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='aip'))
    profile_aip_description = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='aip_description'))
    profile_dip = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='dip'))
    profile_workflow = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='workflow'))
    profile_preservation_metadata = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='preservation_metadata'))
    profile_event = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='event'))
    profile_validation = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='validation'))
    profile_transformation = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='transformation'))

    def validate(self, data):
        if self.instance is None and SubmissionAgreement.objects.filter(pk=data.get('id')).exists():
            raise Conflict('Submission agreement already exists')

        return data

    class Meta:
        model = SubmissionAgreement
        fields = (
                'id', 'name', 'published', 'type', 'status', 'label',

                'cm_version',
                'cm_release_date',
                'cm_change_authority',
                'cm_change_description',
                'cm_sections_affected',

                'producer_organization',
                'producer_main_name',
                'producer_main_address',
                'producer_main_phone',
                'producer_main_email',
                'producer_main_additional',
                'producer_individual_name',
                'producer_individual_role',
                'producer_individual_phone',
                'producer_individual_email',
                'producer_individual_additional',

                'archivist_organization',
                'archivist_main_name',
                'archivist_main_address',
                'archivist_main_phone',
                'archivist_main_email',
                'archivist_main_additional',
                'archivist_individual_name',
                'archivist_individual_role',
                'archivist_individual_phone',
                'archivist_individual_email',
                'archivist_individual_additional',

                'designated_community_description',
                'designated_community_individual_name',
                'designated_community_individual_role',
                'designated_community_individual_phone',
                'designated_community_individual_email',
                'designated_community_individual_additional',

                'information_packages',
                'include_profile_transfer_project',
                'include_profile_content_type',
                'include_profile_data_selection',
                'include_profile_authority_information',
                'include_profile_archival_description', 'include_profile_import',
                'include_profile_submit_description', 'include_profile_sip',
                'include_profile_aip', 'include_profile_dip',
                'include_profile_workflow',
                'include_profile_preservation_metadata',

                'profile_transfer_project',
                'profile_content_type',
                'profile_data_selection',
                'profile_authority_information',
                'profile_archival_description',
                'profile_import',
                'profile_submit_description',
                'profile_sip',
                'profile_aic_description',
                'profile_aip',
                'profile_aip_description',
                'profile_dip',
                'profile_workflow',
                'profile_preservation_metadata',
                'profile_event',
                'profile_validation',
                'profile_transformation',

                'template',
        )

        read_only_fields = ('information_packages',)

        extra_kwargs = {
            'id': {
                'read_only': False,
                'required': False,
            },
        }


class ProfileSerializer(serializers.ModelSerializer):
    specification_data = serializers.SerializerMethodField()
    template = serializers.SerializerMethodField()

    def get_specification_data(self, obj):
        data = obj.specification_data
        request = self.context.get('request')
        if request:
            sa = SubmissionAgreement.objects.filter(
                pk=request.GET.get('sa')
            ).first()
            ip = InformationPackage.objects.filter(
                pk=request.GET.get('ip')
            ).first()

            if not sa and ip:
                sa = ip.submission_agreement

            data = obj.fill_specification_data(sa, ip)

        return data

    def get_template(self, obj):
        data = fill_specification_data()

        for field in obj.template:
            try:
                defaultValue = field['defaultValue']
                if defaultValue in data:
                    field['defaultValue'] = data[defaultValue]
            except KeyError:
                continue

        return obj.template

    def validate(self, data):
        if self.instance is None and Profile.objects.filter(pk=data.get('id')).exists():
            raise Conflict('Profile already exists')

        return data

    class Meta:
        model = Profile
        fields = (
            'id', 'profile_type', 'name', 'type', 'status', 'label',
            'schemas', 'representation_info', 'preservation_descriptive_info',
            'supplemental', 'access_constraints', 'datamodel_reference',
            'cm_release_date', 'cm_change_authority', 'cm_change_description',
            'cm_sections_affected', 'cm_version', 'additional',
            'submission_method', 'submission_schedule',
            'submission_data_inventory', 'structure', 'template',
            'specification_data',
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'required': False,
            },
            'cm_change_description': {
                'required': False,
                'allow_blank': True,
            },
            'cm_change_authority': {
                'required': False,
                'allow_blank': True,
            },
            'cm_version': {
                'required': False,
                'allow_blank': True,
            },
            'cm_sections_affected': {
                'required': False,
                'allow_blank': True,
            },
            'cm_release_date': {
                'required': False,
                'allow_blank': True,
            },
            'representation_info': {
                'required': False,
                'allow_blank': True,
            },
            'preservation_descriptive_info': {
                'required': False,
                'allow_blank': True,
            },
            'supplemental': {
                'required': False,
                'allow_blank': True,
            },
            'access_constraints': {
                'required': False,
                'allow_blank': True,
            },
            'datamodel_reference': {
                'required': False,
                'allow_blank': True,
            },
            'additional': {
                'required': False,
                'allow_blank': True,
            },
            'submission_method': {
                'required': False,
                'allow_blank': True,
            },
            'submission_schedule': {
                'required': False,
                'allow_blank': True,
            },
            'submission_data_inventory': {
                'required': False,
                'allow_blank': True,
            },
        }


class ProfileDetailSerializer(ProfileSerializer):
    class Meta:
        model = ProfileSerializer.Meta.model
        fields = ProfileSerializer.Meta.fields + (
            'specification',
        )
        extra_kwargs = ProfileSerializer.Meta.extra_kwargs


class ProfileWriteSerializer(ProfileDetailSerializer):
    template = serializers.JSONField(default={})

    class Meta:
        model = ProfileDetailSerializer.Meta.model
        fields = ProfileDetailSerializer.Meta.fields
        extra_kwargs = ProfileDetailSerializer.Meta.extra_kwargs
