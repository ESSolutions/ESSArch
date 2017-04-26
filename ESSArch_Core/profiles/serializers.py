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

from ESSArch_Core.ip.models import (
    InformationPackage,
)

from ESSArch_Core.profiles.models import (
    SubmissionAgreement,
    Profile,
    ProfileSA,
    ProfileIP
)


class ProfileSASerializer(serializers.HyperlinkedModelSerializer):
    profile_type = serializers.SlugRelatedField(slug_field='profile_type', source='profile', read_only=True)
    profile_name = serializers.SlugRelatedField(slug_field='name', source='profile', read_only=True)

    class Meta:
        model = ProfileSA
        fields = (
            'url', 'id', 'profile', 'submission_agreement', 'profile_name', 'profile_type', 'LockedBy', 'Unlockable'
        )


class ProfileIPSerializer(serializers.HyperlinkedModelSerializer):
    profile_type = serializers.SlugRelatedField(slug_field='profile_type', source='profile', read_only=True)
    profile_name = serializers.SlugRelatedField(slug_field='name', source='profile', read_only=True)

    class Meta:
        model = ProfileIP
        fields = (
            'url', 'id', 'profile', 'ip', 'profile_name', 'profile_type', 'included', 'LockedBy', 'Unlockable',
        )


class SubmissionAgreementSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    profiles = ProfileSASerializer(many=True)

    def to_representation(self, obj):
        data = super(SubmissionAgreementSerializer, self).to_representation(obj)
        profiles = data['profiles']
        data['profiles'] = {}

        types = [
            'transfer_project', 'content_type', 'data_selection',
            'authority_information', 'archival_description',
            'import', 'submit_description', 'sip', 'aip',
            'dip', 'workflow', 'preservation_metadata',
        ]

        for ptype in types:
            data['profile_%s' % ptype] = None

        for p in profiles:
            data['profile_%s' % p['profile_type']] = p

        data.pop('profiles', None)

        return data

    class Meta:
        model = SubmissionAgreement
        fields = (
                'url', 'id', 'name', 'type', 'status', 'label',

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

                'information_packages', 'profiles',
                'include_profile_transfer_project',
                'include_profile_content_type',
                'include_profile_data_selection',
                'include_profile_authority_information',
                'include_profile_archival_description', 'include_profile_import',
                'include_profile_submit_description', 'include_profile_sip',
                'include_profile_aip', 'include_profile_dip',
                'include_profile_workflow',
                'include_profile_preservation_metadata',
        )


class ProfileSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    specification_data = serializers.SerializerMethodField()

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
                sa = ip.SubmissionAgreement

            data = obj.fill_specification_data(sa, ip)

        return data

    class Meta:
        model = Profile
        fields = (
            'url', 'id', 'profile_type', 'name', 'type', 'status', 'label',
            'schemas', 'representation_info', 'preservation_descriptive_info',
            'supplemental', 'access_constraints', 'datamodel_reference',
            'cm_release_date', 'cm_change_authority', 'cm_change_description',
            'cm_sections_affected', 'cm_version', 'additional',
            'submission_method', 'submission_schedule',
            'submission_data_inventory', 'structure', 'template',
            'specification_data',
        )
