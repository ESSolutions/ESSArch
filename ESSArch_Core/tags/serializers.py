import elasticsearch
from django.core.cache import cache
from django.db import transaction
from rest_framework import serializers

from ESSArch_Core.agents.models import Agent, AgentTagLink, AgentTagLinkRelationType
from ESSArch_Core.agents.serializers import (
    AgentNameSerializer,
    AgentTagLinkRelationTypeSerializer,
)
from ESSArch_Core.ip.utils import get_cached_objid
from ESSArch_Core.tags.models import (
    MediumType,
    NodeIdentifier,
    NodeNote,
    NodeRelationType,
    RuleConventionType,
    Structure,
    StructureUnit,
    StructureUnitRelation,
    Tag,
    TagStructure,
    TagVersion,
    TagVersionRelation,
)


class NodeIdentifierSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='type.name')

    class Meta:
        model = NodeIdentifier
        fields = ('id', 'type', 'identifier',)


class NodeNoteSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='type.name')

    class Meta:
        model = NodeNote
        fields = ('id', 'type', 'text', 'href', 'create_date', 'revise_date',)


class NodeRelationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodeRelationType
        fields = ('id', 'name',)


class RuleConventionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleConventionType
        fields = ('name',)


class StructureSerializer(serializers.ModelSerializer):
    rule_convention_type = RuleConventionTypeSerializer()
    specification = serializers.JSONField(default={})

    class Meta:
        model = Structure
        fields = ('id', 'name', 'version', 'create_date', 'start_date', 'end_date', 'specification',
                  'rule_convention_type',)


class StructureWriteSerializer(StructureSerializer):
    rule_convention_type = serializers.PrimaryKeyRelatedField(
        queryset=RuleConventionType.objects.all(), allow_null=True, default=None
    )


class RelatedStructureUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = StructureUnit
        fields = ('id', 'name',)


class StructureUnitRelationSerializer(serializers.ModelSerializer):
    structure_unit = RelatedStructureUnitSerializer(source='structure_unit_b')
    type = NodeRelationTypeSerializer()

    class Meta:
        model = StructureUnitRelation
        fields = ('type', 'description', 'start_date', 'end_date', 'create_date', 'revise_date', 'structure_unit',)


class StructureUnitRelationWriteSerializer(StructureUnitRelationSerializer):
    structure_unit = serializers.PrimaryKeyRelatedField(
        source='structure_unit_b', queryset=StructureUnit.objects.all()
    )
    type = serializers.PrimaryKeyRelatedField(queryset=NodeRelationType.objects.all())


class StructureUnitSerializer(serializers.ModelSerializer):
    identifiers = NodeIdentifierSerializer(many=True)
    notes = NodeNoteSerializer(many=True)
    is_leaf_node = serializers.SerializerMethodField()
    is_unit_leaf_node = serializers.SerializerMethodField()
    related_structure_units = StructureUnitRelationSerializer(
        source='structure_unit_relations_a', many=True, required=False
    )

    archive = serializers.SerializerMethodField()

    def get_archive(self, obj):
        return obj.structure.tagstructure_set.filter(
            tag__current_version__elastic_index='archive'
        ).first().tag.current_version.pk

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
            'related_structure_units', 'archive',
        )


class StructureUnitWriteSerializer(StructureUnitSerializer):
    related_structure_units = StructureUnitRelationWriteSerializer(
        source='structure_unit_relations_a', many=True, required=False
    )

    @staticmethod
    def create_relations(structure_unit, structure_unit_relations):
        StructureUnitRelation.objects.bulk_create([
            StructureUnitRelation(structure_unit_a=structure_unit, **relation)
            for relation in structure_unit_relations
        ])

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
            StructureUnitRelation.objects.filter(structure_unit_a=instance).delete()
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

    def get_root(self, obj):
        root = obj.get_root()
        if root is not None:
            return root.pk

        return None

    def get_structure_unit(self, obj):
        try:
            unit = obj.get_active_structure().structure_unit
        except TagStructure.DoesNotExist:
            return None

        if unit is None:
            return None

        archive = obj.get_active_structure().get_root().pk
        context = {'archive_structure': archive}
        return StructureUnitSerializer(unit, context=context).data

    def get_is_leaf_node(self, obj):
        return obj.is_leaf_node(structure=self.context.get('structure'))

    def get_masked_fields(self, obj):
        cache_key = u'{}_masked_fields'.format(obj.pk)
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
        fields = ('_id', '_index', 'name', 'type', 'create_date', 'revise_date', 'start_date', 'related_tags', 'notes',
                  'end_date', 'is_leaf_node', '_source', 'masked_fields', 'structure_unit', 'root', 'medium_type',
                  'identifiers', 'agents',)


class AgentArchiveLinkSerializer(serializers.ModelSerializer):
    archive = TagVersionNestedSerializer(source='tag')
    type = AgentTagLinkRelationTypeSerializer()

    class Meta:
        model = AgentTagLink
        fields = ('id', 'archive', 'type', 'description', 'start_date', 'end_date',)


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
