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
import uuid

from rest_framework import serializers

from ESSArch_Core.api.serializers import DynamicHyperlinkedModelSerializer
from ESSArch_Core.configuration.models import (
    Agent,
    ArchivePolicy,
    EventType,
    Parameter,
    Path,
    Site,
)
from ESSArch_Core.storage.models import StorageMethod, StorageTarget, StorageMethodTargetRelation


class EventTypeSerializer(DynamicHyperlinkedModelSerializer):
    class Meta:
        model = EventType
        fields = ('url', 'eventType', 'eventDetail',)


class AgentSerializer(DynamicHyperlinkedModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Agent
        fields = '__all__'


class ParameterSerializer(DynamicHyperlinkedModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Parameter
        fields = '__all__'


class PathSerializer(DynamicHyperlinkedModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Path
        fields = '__all__'
        extra_kwargs = {
            'entity': {
                'validators': [],
            },
        }


class ArchivePolicySerializer(DynamicHyperlinkedModelSerializer):
    cache_storage = PathSerializer()
    ingest_path = PathSerializer()

    class Meta:
        model = ArchivePolicy
        fields = (
            "url", "id", "index", "cache_extracted_size",
            "cache_package_size", "cache_extracted_age",
            "cache_package_age", "policy_id", "policy_name",
            "policy_stat", "ais_project_name", "ais_project_id",
            "mode", "wait_for_approval", "checksum_algorithm",
            "validate_checksum", "validate_xml", "ip_type",
            "preingest_metadata", "ingest_metadata",
            "information_class", "ingest_delete",
            "receive_extract_sip", "cache_storage", "ingest_path",
            "storage_methods",
        )
        extra_kwargs = {
            'id': {
                'validators': [],
            },
            'policy_id': {
                'validators': [],
            },
        }


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ('name', 'logo',)


class ArchivePolicyNestedSerializer(ArchivePolicySerializer):
    class Meta:
        model = ArchivePolicy
        fields = (
            "id", "index", "cache_extracted_size",
            "cache_package_size", "cache_extracted_age",
            "cache_package_age", "policy_id", "policy_name",
            "policy_stat", "ais_project_name", "ais_project_id",
            "mode", "wait_for_approval", "checksum_algorithm",
            "validate_checksum", "validate_xml", "ip_type",
            "preingest_metadata", "ingest_metadata",
            "information_class", "ingest_delete",
            "receive_extract_sip", "cache_storage", "ingest_path",
        )
        extra_kwargs = {
            'id': {
                'validators': [],
            },
            'policy_id': {
                'validators': [],
            },
        }


class StorageTargetSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = StorageTarget
        fields = (
            'url', 'id', 'name', 'status', 'type', 'default_block_size', 'default_format', 'min_chunk_size',
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


class StorageMethodTargetRelationSerializer(serializers.HyperlinkedModelSerializer):
    storage_method = serializers.UUIDField(format='hex_verbose', source='storage_method.id', validators=[])
    storage_target = StorageTargetSerializer()

    class Meta:
        model = StorageMethodTargetRelation
        fields = (
            'url', 'id', 'name', 'status', 'storage_target', 'storage_method',
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'validators': [],
                'default': uuid.uuid4,
            },
        }


class StorageMethodSerializer(DynamicHyperlinkedModelSerializer):
    archive_policy = ArchivePolicyNestedSerializer()
    targets = serializers.PrimaryKeyRelatedField(
        pk_field=serializers.UUIDField(format='hex_verbose'),
        many=True, read_only=True
    )
    storage_method_target_relations = StorageMethodTargetRelationSerializer(validators=[], many=True)

    class Meta:
        model = StorageMethod
        fields = (
            'url', 'id', 'name', 'status', 'type', 'archive_policy', 'targets',
            'storage_method_target_relations',
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'validators': [],
                'default': uuid.uuid4,
            },
        }

