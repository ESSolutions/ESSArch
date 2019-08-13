<<<<<<< HEAD
import elasticsearch
from django.core.cache import cache
=======
import uuid

import elasticsearch
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
>>>>>>> origin/tag-agents
from django.utils.translation import ugettext as _
from rest_framework import serializers
from rest_framework.fields import CurrentUserDefault
from rest_framework.validators import UniqueTogetherValidator

from ESSArch_Core.agents.models import Agent, AgentTagLink, AgentTagLinkRelationType
from ESSArch_Core.agents.serializers import (
    AgentSerializer,
    AgentNameSerializer,
    AgentTagLinkRelationTypeSerializer,
)
from ESSArch_Core.auth.serializers import UserSerializer
from ESSArch_Core.api.validators import StartDateEndDateValidator
from ESSArch_Core.ip.utils import get_cached_objid
<<<<<<< HEAD
from ESSArch_Core.tags.models import (
    Structure,
    StructureUnit,
    Tag,
    TagStructure,
    TagVersion,
)
=======
from ESSArch_Core.profiles.models import SubmissionAgreement
from ESSArch_Core.profiles.serializers import SubmissionAgreementSerializer
from ESSArch_Core.tags.models import (
    Delivery,
    DeliveryType,
    Location,
    LocationFunctionType,
    LocationLevelType,
    MediumType,
    MetricProfile,
    MetricType,
    NodeIdentifier,
    NodeIdentifierType,
    NodeNote,
    NodeNoteType,
    NodeRelationType,
    RuleConventionType,
    Structure,
    StructureType,
    StructureUnit,
    StructureUnitType,
    StructureUnitRelation,
    NodeRelationType,
    Tag,
    TagStructure,
    TagVersion,
    TagVersionRelation,
    TagVersionType,
    Transfer,
)

PUBLISHED_STRUCTURE_CHANGE_ERROR = _('Published structures cannot be changed')


class NodeIdentifierTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodeIdentifierType
        fields = ('id', 'name',)


class NodeIdentifierSerializer(serializers.ModelSerializer):
    type = NodeIdentifierTypeSerializer()

    class Meta:
        model = NodeIdentifier
        fields = ('id', 'type', 'identifier',)


class NodeIdentifierWriteSerializer(NodeIdentifierSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=NodeIdentifierType.objects.all())

    class Meta:
        model = NodeIdentifier
        fields = ('type', 'identifier',)

class NodeNoteTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodeNoteType
        fields = ('id', 'name',)


class NodeNoteSerializer(serializers.ModelSerializer):
    type = NodeNoteTypeSerializer()

    class Meta:
        model = NodeNote
        fields = ('id', 'type', 'text', 'href', 'create_date', 'revise_date',)


class NodeNoteWriteSerializer(NodeNoteSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=NodeNoteType.objects.all())

    class Meta(NodeNoteSerializer.Meta):
        extra_kwargs = {
            'create_date': {
                'default': timezone.now,
            },
        }


class NodeRelationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodeRelationType
        fields = ('id', 'name',)


class RuleConventionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleConventionType
        fields = ('name',)


class StructureTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StructureType
        fields = (
            'id', 'name', 'instance_name', 'editable_instances',
            'movable_instance_units', 'editable_instance_relations',
        )
>>>>>>> origin/tag-agents


class StructureSerializer(serializers.ModelSerializer):
    type = StructureTypeSerializer()
    rule_convention_type = RuleConventionTypeSerializer()
    specification = serializers.JSONField(default={})
    created_by = UserSerializer(read_only=True, default=serializers.CurrentUserDefault())
    revised_by = UserSerializer(read_only=True, default=serializers.CurrentUserDefault())

    class Meta:
        model = Structure
        fields = ('id', 'name', 'type', 'template', 'is_template', 'version', 'create_date', 'revise_date',
                  'start_date', 'end_date', 'specification', 'rule_convention_type', 'created_by', 'revised_by',
                  'published', 'published_date',)
        extra_kwargs = {
            'is_template': {'read_only': True},
            'template': {'read_only': True},
        }


class StructureWriteSerializer(StructureSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=StructureType.objects.all())
    rule_convention_type = serializers.PrimaryKeyRelatedField(
        queryset=RuleConventionType.objects.all(), allow_null=True, default=None
    )
    version_link = serializers.UUIDField(default=uuid.uuid4, allow_null=False)

    def validate(self, data):
        if self.instance and self.instance.published:
            raise serializers.ValidationError(PUBLISHED_STRUCTURE_CHANGE_ERROR)

        return data

    def create(self, validated_data):
        validated_data['is_template'] = True
        validated_data['created_by'] = self.context['request'].user
        validated_data['revised_by'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data['revised_by'] = self.context['request'].user
        return super().update(instance, validated_data)

    class Meta(StructureSerializer.Meta):
        fields = StructureSerializer.Meta.fields + ('version_link',)
        validators = [
            StartDateEndDateValidator(
                start_date='start_date',
                end_date='end_date',
            ),
            UniqueTogetherValidator(
                queryset=Structure.objects.all(),
                fields=('version_link', 'version'),
            ),
        ]
        extra_kwargs = {
            'version': {
                'default': '1.0',
            }
        }


class RelatedStructureUnitSerializer(serializers.ModelSerializer):
    structure = StructureSerializer(read_only=True)

    class Meta:
        model = StructureUnit
        fields = ('id', 'name', 'structure')


class StructureUnitRelationSerializer(serializers.ModelSerializer):
    structure_unit = RelatedStructureUnitSerializer(source='structure_unit_b')
    type = NodeRelationTypeSerializer()

    class Meta:
        model = StructureUnitRelation
        fields = ('id', 'type', 'description', 'start_date', 'end_date',
                  'create_date', 'revise_date', 'structure_unit',)


class StructureUnitRelationWriteSerializer(StructureUnitRelationSerializer):
    structure_unit = serializers.PrimaryKeyRelatedField(
        source='structure_unit_b', queryset=StructureUnit.objects.all()
    )
    type = serializers.PrimaryKeyRelatedField(queryset=NodeRelationType.objects.all())


class NodeRelationTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = NodeRelationType
        fields = ('id', 'name',)


class StructureUnitTypeSerializer(serializers.ModelSerializer):
    structure_type = StructureTypeSerializer()

    class Meta:
        model = StructureUnitType
        fields = ('id', 'name', 'structure_type',)


class StructureUnitSerializer(serializers.ModelSerializer):
    type = StructureUnitTypeSerializer()
    identifiers = NodeIdentifierSerializer(many=True, read_only=True)
    notes = NodeNoteSerializer(many=True, read_only=True)
    is_leaf_node = serializers.SerializerMethodField()
    is_unit_leaf_node = serializers.SerializerMethodField()
    related_structure_units = StructureUnitRelationSerializer(
        source='structure_unit_relations_a', many=True, required=False
    )

    archive = serializers.SerializerMethodField(read_only=True)

    def get_archive(self, obj):
        tag_structure = obj.structure.tagstructure_set.filter(
            tag__current_version__elastic_index='archive'
        ).first()

        if tag_structure is not None:
            return tag_structure.tag.current_version.pk

        return None

    def get_is_unit_leaf_node(self, obj):
        return obj.is_leaf_node()

    def get_is_leaf_node(self, obj):
        archive_descendants = obj.structure.tagstructure_set.filter(structure_unit=obj)
        return obj.is_leaf_node() and not archive_descendants.exists()

    class Meta:
        model = StructureUnit
        fields = (
            'id', 'parent', 'name', 'type', 'description',
            'reference_code', 'start_date', 'end_date', 'is_leaf_node',
            'is_unit_leaf_node', 'structure', 'identifiers', 'notes',
            'related_structure_units', 'archive', 'structure',
        )


class StructureUnitWriteSerializer(StructureUnitSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=StructureUnitType.objects.all())
    related_structure_units = StructureUnitRelationWriteSerializer(
        source='structure_unit_relations_a', many=True, required=False
    )

    def validate(self, data):
        structure = data.pop('structure', None)

        if structure is not None and not structure.is_template:
            tag_structure = structure.tagstructure_set.first()
            if tag_structure is not None:
                archive = tag_structure.get_root().tag
                for relation in data.get('structure_unit_relations_a', []):
                    related_structure = relation['structure_unit_b'].structure
                    if structure != related_structure:
                        if related_structure.tagstructure_set.exclude(tag=archive).exists():
                            raise serializers.ValidationError(
                                _('Units in instances cannot relate to units in another archive')
                            )

        if self.instance and not self.instance.structure.is_template:
            structure_type = self.instance.structure.type

            if 'structure_unit_relations_a' in data:
                if not structure_type.editable_instance_relations:
                    raise serializers.ValidationError(
                        _('Unit relations in instances of type {} cannot be edited').format(structure_type)
                    )

        if set(data.keys()) == {'structure_unit_relations_a'}:
            return data

        if not self.instance:
            if not structure.is_template and not structure.type.editable_instances:
                raise serializers.ValidationError(
                    _('Cannot create units in instances of type {}').format(structure.type)
                )

        if self.instance and not self.instance.structure.is_template:
            structure_type = self.instance.structure.type

            # are we moving?
            copied = data.copy()
            if 'parent' in copied:
                if not structure_type.movable_instance_units:
                    raise serializers.ValidationError(
                        _('Units in instances of type {} cannot be moved').format(structure_type)
                    )

                copied.pop('parent', None)

            copied.pop('structure_unit_relations_a', None)

            # are we editing?
            if len(copied.keys()) > 0:
                if not structure_type.editable_instances:
                    raise serializers.ValidationError(
                        _('Units in instances of type {} cannot be edited').format(structure_type)
                    )

        if self.instance and self.instance.structure.is_template and self.instance.structure.published:
            raise serializers.ValidationError(PUBLISHED_STRUCTURE_CHANGE_ERROR)

        unit_type = data.get('type')

        if structure is not None and unit_type is not None:
            if structure.is_template and structure.published:
                raise serializers.ValidationError(PUBLISHED_STRUCTURE_CHANGE_ERROR)

            if structure.type != unit_type.structure_type:
                raise serializers.ValidationError(
                    _('Unit type {} is not allowed in structure type {}').format(unit_type.name, structure.type.name)
                )

        data['structure'] = structure

        if data['structure'] is not None and 'parent' in data and data['parent'] is not None:
            if data['parent'].structure != data['structure']:
                raise serializers.ValidationError(
                    _('Parent and child structure unit must be in the same structure')
                )

        return super().validate(data)

    @staticmethod
    def create_relations(structure_unit, structure_unit_relations):
        for relation in structure_unit_relations:
            other_unit = relation.pop('structure_unit_b')
            relation_type = relation.pop('type')
            structure_unit.relate_to(other_unit, relation_type, **relation)

    @transaction.atomic
    def create(self, validated_data):
        related_units_data = validated_data.pop('structure_unit_relations_a', [])
        unit = StructureUnit.objects.create(**validated_data)

        self.create_relations(unit, related_units_data)

        return unit

    @transaction.atomic
    def update(self, instance, validated_data):
        related_units_data = validated_data.pop('structure_unit_relations_a', None)

        if related_units_data is not None:
            StructureUnitRelation.objects.filter(Q(structure_unit_a=instance) | Q(structure_unit_b=instance)).delete()
            self.create_relations(instance, related_units_data)

        return super().update(instance, validated_data)


class TagStructureSerializer(serializers.ModelSerializer):
    structure = StructureSerializer(read_only=True)

    class Meta:
        model = TagStructure
        fields = ('id', 'parent', 'structure')
        read_only_fields = ('parent', 'structure',)


class MediumTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediumType
        fields = ('id', 'name', 'size', 'unit',)


class TagVersionSerializerWithoutSource(serializers.ModelSerializer):
    class Meta:
        model = TagVersion
        fields = ('id', 'elastic_index', 'name', 'type', 'create_date', 'start_date',
                  'end_date',)


class TagVersionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TagVersion
        fields = ('start_date', 'end_date', 'name', 'type', 'reference_code',)


class RelatedTagVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TagVersion
        fields = ('id', 'name',)


class TagVersionRelationSerializer(serializers.ModelSerializer):
    tag_version = RelatedTagVersionSerializer(source='tag_version_b')
    type = serializers.CharField(source='type.name')

    class Meta:
        model = TagVersionRelation
        fields = ('tag_version', 'type')


class TagVersionAgentTagLinkAgentSerializer(serializers.ModelSerializer):
    names = AgentNameSerializer(many=True)

    class Meta:
        model = Agent
        fields = ('id', 'names', 'create_date', 'revise_date', 'start_date', 'end_date',)


class TagVersionAgentTagLinkSerializer(serializers.ModelSerializer):
    agent = TagVersionAgentTagLinkAgentSerializer()
    type = serializers.CharField(source='type.name')

    class Meta:
        model = AgentTagLink
        fields = ('agent', 'type', 'start_date', 'end_date', 'description',)


class TagVersionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TagVersionType
        fields = ('pk', 'name', 'archive_type',)


class MetricTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricType
        fields = ('id', 'name',)


class MetricProfileSerializer(serializers.ModelSerializer):
    metric = MetricTypeSerializer()

    class Meta:
        model = MetricProfile
        fields = ('id', 'name', 'capacity', 'metric',)


class LocationLevelTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationLevelType
        fields = ('id', 'name',)


class LocationFunctionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationFunctionType
        fields = ('id', 'name',)


class LocationSerializer(serializers.ModelSerializer):
    metric = MetricProfileSerializer()
    level_type = LocationLevelTypeSerializer()
    function = LocationFunctionTypeSerializer()

    class Meta:
        model = Location
        fields = ('id', 'name', 'parent', 'level_type', 'function', 'metric',)


class LocationWriteSerializer(LocationSerializer):
    metric = serializers.PrimaryKeyRelatedField(
        allow_null=True, required=False, default=None,
        queryset=MetricProfile.objects.all(),
    )
    level_type = serializers.PrimaryKeyRelatedField(queryset=LocationLevelType.objects.all())
    function = serializers.PrimaryKeyRelatedField(queryset=LocationFunctionType.objects.all())

    @transaction.atomic
    def create(self, validated_data):
        location = super().create(validated_data)
        user = self.context['request'].user

        organization = user.user_profile.current_organization
        organization.assign_object(location)
        organization.add_object(location)

        return location

    class Meta(LocationSerializer.Meta):
        fields = ('name', 'parent', 'level_type', 'function', 'metric')


class TagVersionNestedSerializer(serializers.ModelSerializer):
    _id = serializers.UUIDField(source='pk')
    _index = serializers.CharField(source='elastic_index')
    is_leaf_node = serializers.SerializerMethodField()
    _source = serializers.SerializerMethodField()
    masked_fields = serializers.SerializerMethodField()
    structure_unit = serializers.SerializerMethodField()
    root = serializers.SerializerMethodField()
    related_tags = TagVersionRelationSerializer(source='tag_version_relations_a', many=True)
    medium_type = MediumTypeSerializer()
    notes = NodeNoteSerializer(many=True)
    identifiers = NodeIdentifierSerializer(many=True)
    agents = TagVersionAgentTagLinkSerializer(source='agent_links', many=True)
    type = TagVersionTypeSerializer()
    metric = MetricProfileSerializer()
    location = LocationSerializer()
    custom_fields = serializers.JSONField()

    def get_root(self, obj):
        root = obj.get_root()
        if root is not None:
            return root.pk

        return None

    def get_structure_unit(self, obj):
        structure = self.context.get('structure')

        try:
            if structure is not None:
                tag_structure = obj.tag.structures.get(structure=structure)
            else:
                tag_structure = obj.get_active_structure()
        except TagStructure.DoesNotExist:
            return None

        unit = tag_structure.structure_unit

        if unit is None:
            return None

        archive = tag_structure.get_root().pk
        context = {'archive_structure': archive}
        return StructureUnitSerializer(unit, context=context).data

    def get_is_leaf_node(self, obj):
        return obj.is_leaf_node(structure=self.context.get('structure'))

    def get_masked_fields(self, obj):
        cache_key = '{}_masked_fields'.format(obj.pk)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            doc = obj.get_doc()
            masked = doc.get_masked_fields(self.context.get('user'))
            cache.set(cache_key, masked, 60)
            return masked
        except elasticsearch.NotFoundError:
            return []

    def get__source(self, obj):
        hidden_fields = ['restrictions']
        try:
            doc = obj.get_doc()
            masked_fields = self.get_masked_fields(obj)
            d = doc.to_dict()

            try:
                d['ip_objid'] = get_cached_objid(d['ip'])
            except KeyError:
                pass

            if doc._index == 'document':
                try:
                    d['attachment'].pop('content', None)
                except KeyError:
                    pass
            for field in d.keys():
                if field in masked_fields:
                    d[field] = ''
                if field in hidden_fields:
                    d.pop(field)
            return d
        except elasticsearch.NotFoundError:
            return None

    class Meta:
        model = TagVersion
        fields = (
            '_id', '_index', 'name', 'type', 'create_date', 'revise_date',
            'import_date', 'start_date', 'related_tags', 'notes', 'end_date',
            'is_leaf_node', '_source', 'masked_fields', 'structure_unit', 'root',
            'medium_type', 'identifiers', 'agents', 'description', 'reference_code',
            'custom_fields', 'metric', 'location',
        )


class AgentArchiveLinkSerializer(serializers.ModelSerializer):
    archive = TagVersionNestedSerializer(source='tag')
    type = AgentTagLinkRelationTypeSerializer()

    class Meta:
        model = AgentTagLink
        fields = ('id', 'archive', 'type', 'description', 'start_date', 'end_date',)
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=('tag', 'agent'),
                message=_('Archive already added')
            )
        ]


class AgentArchiveLinkWriteSerializer(AgentArchiveLinkSerializer):
    agent = serializers.PrimaryKeyRelatedField(queryset=Agent.objects.all())
    archive = serializers.PrimaryKeyRelatedField(
        source='tag',
        queryset=TagVersion.objects.filter(elastic_index='archive')
    )
    type = serializers.PrimaryKeyRelatedField(queryset=AgentTagLinkRelationType.objects.all())

    class Meta(AgentArchiveLinkSerializer.Meta):
        AgentArchiveLinkSerializer.Meta.fields += ('agent',)


class TagVersionSerializer(TagVersionNestedSerializer):
    structures = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()

    def get_structures(self, obj):
        structure_ids = obj.tag.structures.values_list('structure', flat=True)
        structures = Structure.objects.filter(pk__in=structure_ids).order_by('create_date')
        return StructureSerializer(structures, many=True).data

    def get_parent(self, obj):
        parent = obj.get_parent(structure=self.context.get('structure'))
        if parent is None:
            return None

        return {
            'id': str(parent.pk),
            'index': parent.elastic_index
        }

    class Meta(TagVersionNestedSerializer.Meta):
        fields = TagVersionNestedSerializer.Meta.fields + ('structures', 'parent',)


class TagVersionSerializerWithVersions(TagVersionSerializer):
    versions = serializers.SerializerMethodField()

    def get_versions(self, obj):
        versions = TagVersion.objects.filter(tag=obj.tag).exclude(pk=obj.pk)
        return TagVersionSerializer(versions, many=True, context=self.context).data

    class Meta(TagVersionSerializer.Meta):
        fields = TagVersionSerializer.Meta.fields + ('versions',)


class TagSerializer(serializers.ModelSerializer):
    structures = TagStructureSerializer(many=True, read_only=True)
    current_version = TagVersionSerializerWithoutSource(read_only=True)
    other_versions = serializers.SerializerMethodField()

    def get_other_versions(self, obj):
        versions = obj.versions.exclude(pk=obj.current_version.pk)
        return TagVersionSerializer(versions, many=True, context=self.context).data

    class Meta:
        model = Tag
        fields = ('id', 'current_version', 'other_versions', 'structures')


<<<<<<< HEAD
class SearchSerializer(serializers.Serializer):
    index = serializers.ChoiceField(choices=['archive', 'component'], default='component')
    name = serializers.CharField()
    type = serializers.CharField()
    reference_code = serializers.CharField()
    structure = serializers.PrimaryKeyRelatedField(required=False, queryset=Structure.objects.all())
    archive = serializers.CharField(required=False)
    parent = serializers.CharField(required=False)
    structure_unit = serializers.CharField(required=False)
    archive_creator = serializers.CharField(required=False)
    archive_responsible = serializers.CharField(required=False)

    def validate(self, data):
        if data['index'] == 'archive' and 'structure' not in data:
            raise serializers.ValidationError({'structure': [_('This field is required.')]})

        if data['index'] != 'archive':
            if 'parent' not in data and 'structure_unit' not in data:
                raise serializers.ValidationError('parent or structure_unit required')

            if 'structure_unit' in data and 'archive' not in data:
                raise serializers.ValidationError({'archive': [_('This field is required.')]})

        return data
=======
class DeliveryTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryType
        fields = ('id', 'name')


class DeliverySerializer(serializers.ModelSerializer):
    type = DeliveryTypeSerializer()
    submission_agreement = SubmissionAgreementSerializer()
    producer_organization = AgentSerializer()

    class Meta:
        model = Delivery
        fields = ('id', 'name', 'type', 'description', 'submission_agreement', 'producer_organization', 'reference_code')


class DeliveryWriteSerializer(DeliverySerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=DeliveryType.objects.all())
    submission_agreement = serializers.PrimaryKeyRelatedField(
        queryset=SubmissionAgreement.objects.filter(published=True), allow_null=True)
    producer_organization = serializers.PrimaryKeyRelatedField(queryset=Agent.objects.all(), allow_null=True)

    def create(self, validated_data):
        obj = super().create(validated_data)

        org = self.context['request'].user.user_profile.current_organization
        org.add_object(obj)

        return obj


class TransferSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        obj = super().create(validated_data)

        org = self.context['request'].user.user_profile.current_organization
        org.add_object(obj)

        return obj

    class Meta:
        model = Transfer
        fields = ('id', 'name', 'delivery', 'submitter_organization', 'submitter_organization_main_address',
                  'submitter_individual_name', 'submitter_individual_phone', 'submitter_individual_email', 'description')


class TransferEditNodesSerializer(serializers.Serializer):
    tags = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(
            queryset=TagVersion.objects.all(),
        )
    )
    structure_units = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(
            queryset=StructureUnit.objects.filter(structure__is_template=False),
        )
    )
>>>>>>> origin/tag-agents
