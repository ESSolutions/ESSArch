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
                'url', 'id', 'sa_name', 'sa_type', 'sa_status', 'sa_label',
                'sa_cm_version', 'sa_cm_release_date',
                'sa_cm_change_authority', 'sa_cm_change_description',
                'sa_cm_sections_affected', 'sa_producer_organization',
                'sa_producer_main_name', 'sa_producer_main_address',
                'sa_producer_main_phone', 'sa_producer_main_email',
                'sa_producer_main_additional', 'sa_producer_individual_name',
                'sa_producer_individual_role', 'sa_producer_individual_phone',
                'sa_producer_individual_email',
                'sa_producer_individual_additional',
                'sa_archivist_organization', 'sa_archivist_main_name',
                'sa_archivist_main_address', 'sa_archivist_main_phone',
                'sa_archivist_main_email', 'sa_archivist_main_additional',
                'sa_archivist_individual_name', 'sa_archivist_individual_role',
                'sa_archivist_individual_phone',
                'sa_archivist_individual_email',
                'sa_archivist_individual_additional',
                'sa_designated_community_description',
                'sa_designated_community_individual_name',
                'sa_designated_community_individual_role',
                'sa_designated_community_individual_phone',
                'sa_designated_community_individual_email',
                'sa_designated_community_individual_additional',
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
