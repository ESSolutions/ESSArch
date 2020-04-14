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

import requests
from lxml import etree
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ESSArch_Core.essxml.ProfileMaker.models import (
    extensionPackage,
    templatePackage,
)
from ESSArch_Core.essxml.ProfileMaker.xsdtojson import (
    generateExtensionRef,
    generateJsonRes,
)
from ESSArch_Core.exceptions import Conflict
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.profiles.models import (
    Profile,
    ProfileIP,
    ProfileIPData,
    ProfileIPDataTemplate,
    ProfileSA,
    SubmissionAgreement,
    SubmissionAgreementIPData,
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
    data = serializers.JSONField(required=False)

    def validate(self, data):
        relation = data['relation']
        instance_data = data.get('data', {})

        if self.instance is None and relation.data is not None and instance_data == relation.data.data:
            raise serializers.ValidationError('No changes made')

        validate_template(relation.profile.template, instance_data)
        data['data'] = instance_data
        return data

    def create(self, validated_data):
        if 'user' not in validated_data:
            validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

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


class ProfileIPDataTemplateSerializer(serializers.ModelSerializer):
    data = serializers.JSONField(required=False)

    class Meta:
        model = ProfileIPDataTemplate
        fields = ('id', 'name', 'data', 'created', 'profile')


class ProfileIPSerializer(serializers.ModelSerializer):
    profile = serializers.PrimaryKeyRelatedField(
        queryset=Profile.objects.all(), required=True,
        pk_field=serializers.UUIDField(format='hex_verbose'),
    )
    ip = serializers.PrimaryKeyRelatedField(
        queryset=InformationPackage.objects.all(), required=True,
        pk_field=serializers.UUIDField(format='hex_verbose'),
    )
    profile_type = serializers.SlugRelatedField(slug_field='profile_type', source='profile', read_only=True)
    profile_name = serializers.SlugRelatedField(slug_field='name', source='profile', read_only=True)
    data_versions = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True,
        pk_field=serializers.UUIDField(format='hex_verbose'),
    )

    class Meta:
        model = ProfileIP
        fields = ('id', 'profile', 'ip', 'profile_name', 'profile_type', 'included', 'LockedBy', 'Unlockable',
                  'data_versions',)
        read_only_fields = ('LockedBy', 'data_versions',)


class ProfileIPSerializerWithData(ProfileIPSerializer):
    data = serializers.SerializerMethodField()

    def get_data(self, obj):
        if obj.data is not None:
            serializer = ProfileIPDataSerializer(obj.data, context={'request': self.context['request']})
            data = serializer.data
        else:
            data = {'data': {}}

        data['data'].update(obj.get_related_profile_data(original_keys=True))
        extra_data = fill_specification_data(ip=obj.ip, sa=obj.ip.submission_agreement)

        for field in obj.profile.template:
            if field['key'] in extra_data:
                data['data'][field['key']] = extra_data[field['key']]

        return data

    class Meta(ProfileIPSerializer.Meta):
        fields = ProfileIPSerializer.Meta.fields + ('data',)
        read_only_fields = ProfileIPSerializer.Meta.read_only_fields + ('data',)


class ProfileIPWriteSerializer(ProfileIPSerializer):
    data = serializers.PrimaryKeyRelatedField(default=None, allow_null=True, queryset=ProfileIPData.objects.all())

    class Meta(ProfileIPSerializer.Meta):
        fields = ProfileIPSerializer.Meta.fields + ('data',)


class SubmissionAgreementSerializer(serializers.ModelSerializer):
    published = serializers.BooleanField(read_only=True)

    profile_transfer_project = serializers.PrimaryKeyRelatedField(
        default=None, allow_null=True,
        queryset=Profile.objects.filter(profile_type='transfer_project')
    )
    profile_content_type = serializers.PrimaryKeyRelatedField(
        default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='content_type')
    )
    profile_data_selection = serializers.PrimaryKeyRelatedField(
        default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='data_selection')
    )
    profile_authority_information = serializers.PrimaryKeyRelatedField(
        default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='authority_information')
    )
    profile_archival_description = serializers.PrimaryKeyRelatedField(
        default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='archival_description')
    )
    profile_import = serializers.PrimaryKeyRelatedField(
        default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='import')
    )
    profile_submit_description = serializers.PrimaryKeyRelatedField(
        default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='submit_description')
    )
    profile_sip = serializers.PrimaryKeyRelatedField(
        default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='sip')
    )
    profile_aic_description = serializers.PrimaryKeyRelatedField(
        default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='aic_description')
    )
    profile_aip = serializers.PrimaryKeyRelatedField(
        default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='aip')
    )
    profile_aip_description = serializers.PrimaryKeyRelatedField(
        default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='aip_description')
    )
    profile_dip = serializers.PrimaryKeyRelatedField(
        default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='dip')
    )
    profile_workflow = serializers.PrimaryKeyRelatedField(
        default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='workflow')
    )
    profile_preservation_metadata = serializers.PrimaryKeyRelatedField(
        default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='preservation_metadata')
    )
    profile_event = serializers.PrimaryKeyRelatedField(
        default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='event')
    )
    profile_validation = serializers.PrimaryKeyRelatedField(
        default=None, allow_null=True, queryset=Profile.objects.filter(profile_type='validation')
    )

    template = serializers.JSONField(required=False)

    def validate(self, data):
        if self.instance is None and SubmissionAgreement.objects.filter(pk=data.get('id')).exists():
            raise Conflict('Submission agreement already exists')

        return data

    class Meta:
        model = SubmissionAgreement
        fields = (
            'id', 'name', 'published', 'type', 'status', 'label', 'policy',

            'archivist_organization',

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

            'template',
        )

        read_only_fields = ('information_packages',)

        extra_kwargs = {
            'id': {
                'read_only': False,
                'required': False,
            },
        }


class SubmissionAgreementIPDataSerializer(serializers.ModelSerializer):
    data = serializers.JSONField(required=False)

    def validate(self, data):
        sa = data.get('submission_agreement', getattr(self.instance, 'submission_agreement', None))
        instance_data = data.get('data', {})

        validate_template(sa.template, instance_data)
        data['data'] = instance_data
        return data

    def create(self, validated_data):
        if 'user' not in validated_data:
            validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    class Meta:
        model = SubmissionAgreementIPData
        fields = (
            'id', 'submission_agreement', 'information_package', 'data', 'version', 'user', 'created',
        )
        extra_kwargs = {
            'user': {
                'read_only': True,
                'default': serializers.CurrentUserDefault(),
            }
        }


class ProfileSerializer(serializers.ModelSerializer):
    specification_data = serializers.SerializerMethodField()
    template = serializers.SerializerMethodField()
    schemas = serializers.JSONField(required=False)
    structure = serializers.JSONField(required=False)

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

            data = fill_specification_data(data=data, sa=sa, ip=ip)

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
            'type': {
                'required': False,
                'allow_blank': True,
            },
            'status': {
                'required': False,
                'allow_blank': True,
            },
            'label': {
                'required': False,
                'allow_blank': True,
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
    specification = serializers.JSONField(required=False)

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


class ProfileIPSerializerWithProfileAndData(ProfileIPSerializerWithData):
    profile = ProfileSerializer()


class ProfileMakerExtensionSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        schema_url = validated_data.pop('schemaURL')
        schema_request = requests.get(schema_url)
        schema_request.raise_for_status()

        schemadoc = etree.fromstring(schema_request.content)

        print(schemadoc.nsmap)
        nsmap = {k: v for k, v in schemadoc.nsmap.items() if k and v != "http://www.w3.org/2001/XMLSchema"}
        targetNamespace = schemadoc.get('targetNamespace')

        prefix = validated_data.pop('prefix')
        extensionElements, extensionAll, attributes = generateExtensionRef(schemadoc, prefix)

        return extensionPackage.objects.create(
            prefix=prefix, schemaURL=schema_url, targetNamespace=targetNamespace,
            allElements=extensionAll, existingElements=extensionElements,
            allAttributes=attributes, nsmap=nsmap, **validated_data
        )

    class Meta:
        model = extensionPackage
        fields = (
            'id', 'allElements', 'existingElements', 'allAttributes', 'prefix', 'schemaURL', 'targetNamespace',
        )

        read_only_fields = (
            'existingElements', 'allElements', 'allAttributes',
        )

        extra_kwargs = {
            'targetNamespace': {
                'required': False
            }
        }


class ProfileMakerTemplateSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        schema_request = requests.get(validated_data['schemaURL'])
        schema_request.raise_for_status()

        schemadoc = etree.fromstring(schema_request.content)
        targetNamespace = schemadoc.get('targetNamespace')
        nsmap = {k: v for k, v in schemadoc.nsmap.items() if k and v != "http://www.w3.org/2001/XMLSchema"}

        try:
            existingElements, allElements = generateJsonRes(
                schemadoc,
                validated_data['root_element'],
                validated_data['prefix']
            )
        except ValueError as e:
            raise ValidationError(e)

        return templatePackage.objects.create(
            existingElements=existingElements, allElements=allElements,
            targetNamespace=targetNamespace, nsmap=nsmap, **validated_data
        )

    class Meta:
        model = templatePackage
        fields = (
            'existingElements', 'allElements', 'name', 'root_element',
            'extensions', 'prefix', 'schemaURL', 'targetNamespace', 'structure'
        )

        read_only_fields = (
            'existingElements', 'allElements',
        )

        extra_kwargs = {
            'extensions': {
                'required': False,
                'allow_empty': True,
            },
            'root_element': {
                'required': True
            },
            'targetNamespace': {
                'required': False
            }
        }
