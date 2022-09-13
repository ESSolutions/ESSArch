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

from rest_framework import serializers

from ESSArch_Core.api.serializers import DynamicModelSerializer
from ESSArch_Core.configuration.models import (
    EventType,
    Feature,
    Parameter,
    Path,
    Site,
    StoragePolicy,
)
from ESSArch_Core.profiles.models import SubmissionAgreement
from ESSArch_Core.storage.models import (
    StorageMethod,
    StorageMethodTargetRelation,
    StorageTarget,
)


class EventTypeSerializer(DynamicModelSerializer):
    class Meta:
        model = EventType
        fields = ('eventType', 'eventDetail',)


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ('name', 'description', 'enabled',)


class ParameterSerializer(DynamicModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Parameter
        fields = '__all__'


class PathSerializer(DynamicModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Path
        fields = '__all__'
        extra_kwargs = {
            'entity': {
                'validators': [],
            },
        }


class StorageTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageTarget
        fields = (
            'id', 'name', 'status', 'type', 'default_block_size', 'default_format', 'min_chunk_size',
            'min_capacity_warning', 'max_capacity', 'remote_server', 'master_server', 'target'
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'default': uuid.uuid4,
            },
            'name': {
                'validators': [],
            },
        }


class StorageMethodTargetRelationSerializer(serializers.ModelSerializer):
    storage_method = serializers.UUIDField(format='hex_verbose', source='storage_method.id', validators=[])
    storage_target = StorageTargetSerializer()

    class Meta:
        model = StorageMethodTargetRelation
        fields = (
            'id', 'name', 'status', 'storage_target', 'storage_method',
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'validators': [],
                'default': uuid.uuid4,
            },
        }


class StorageMethodSerializer(serializers.ModelSerializer):
    targets = serializers.PrimaryKeyRelatedField(
        pk_field=serializers.UUIDField(format='hex_verbose'),
        many=True, read_only=True
    )
    storage_method_target_relations = StorageMethodTargetRelationSerializer(validators=[], many=True)

    class Meta:
        model = StorageMethod
        fields = (
            'id', 'name', 'enabled', 'type', 'targets',
            'containers', 'storage_method_target_relations',
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'validators': [],
                'default': uuid.uuid4,
            },
        }


class StoragePolicySerializer(serializers.ModelSerializer):
    cache_storage = StorageMethodSerializer(allow_null=True)
    storage_methods = StorageMethodSerializer(many=True)
    ingest_path = PathSerializer(allow_null=True)
    sa = serializers.DictField(allow_null=True, required=False, write_only=True)

    def create(self, validated_data):
        storage_method_set_data = validated_data.pop('storage_methods')
        if 'sa' in validated_data.keys():
            sa_data = validated_data.pop('sa')
        else:
            sa_data = None
        storage_method_list = []

        for storage_method_data in storage_method_set_data:
            storage_method_target_set_data = storage_method_data.pop('storage_method_target_relations')
            storage_method, _ = StorageMethod.objects.update_or_create(
                id=storage_method_data['id'],
                defaults=storage_method_data
            )

            for storage_method_target_data in storage_method_target_set_data:
                StorageMethodTargetRelation.objects.filter(id=storage_method_target_data['id']).update(status=0)

            for storage_method_target_data in storage_method_target_set_data:
                storage_target_data = storage_method_target_data.pop('storage_target')
                storage_target, _ = StorageTarget.objects.update_or_create(
                    id=storage_target_data['id'],
                    defaults=storage_target_data
                )
                storage_method_target_data['storage_method'] = storage_method
                storage_method_target_data['storage_target'] = storage_target
                storage_method_target, _ = StorageMethodTargetRelation.objects.update_or_create(
                    id=storage_method_target_data['id'],
                    defaults=storage_method_target_data
                )
            storage_method_list.append(storage_method)

        policy, _ = StoragePolicy.objects.update_or_create(policy_id=validated_data['policy_id'],
                                                           defaults=validated_data)
        policy.storage_methods.set(storage_method_list)
        if sa_data:
            sa_data['policy'] = policy
            if sa_data.get('id', False):
                sa, _ = SubmissionAgreement.objects.update_or_create(id=sa_data['id'], defaults=sa_data)
            else:
                sa, _ = SubmissionAgreement.objects.update_or_create(name=sa_data['name'], defaults=sa_data)

        return policy

    class Meta:
        model = StoragePolicy
        fields = (
            "id", "index",
            "cache_minimum_capacity", "cache_maximum_age",
            "policy_id", "policy_name",
            "policy_stat", "ais_project_name", "ais_project_id",
            "mode", "wait_for_approval", "checksum_algorithm",
            "validate_checksum", "validate_xml", "ip_type",
            "preingest_metadata", "ingest_metadata",
            "information_class", "ingest_delete",
            "receive_extract_sip", "cache_storage", "ingest_path",
            "storage_methods", "sa",
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'validators': [],
                'default': uuid.uuid4,
            },
            'policy_id': {
                'validators': [],
            },
        }


class StoragePolicyNestedSerializer(StoragePolicySerializer):
    class Meta(StoragePolicySerializer.Meta):
        fields = (
            "id", "index",
            "cache_minimum_capacity", "cache_maximum_age",
            "policy_id", "policy_name",
            "policy_stat", "ais_project_name", "ais_project_id",
            "mode", "wait_for_approval", "checksum_algorithm",
            "validate_checksum", "validate_xml", "ip_type",
            "preingest_metadata", "ingest_metadata",
            "information_class", "ingest_delete",
            "receive_extract_sip", "cache_storage", "ingest_path",
        )


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ('name', 'logo', 'title', 'text')
