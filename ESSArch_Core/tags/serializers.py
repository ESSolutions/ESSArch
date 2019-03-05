from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
import elasticsearch
from rest_framework import serializers

from ESSArch_Core.ip.utils import get_cached_objid
from ESSArch_Core.tags.models import (
    Agent,
    AgentIdentifier,
    AgentIdentifierType,
    AgentName,
    AgentNameType,
    AgentNote,
    AgentNoteType,
    AgentPlace,
    AgentPlaceType,
    AgentRelation,
    AgentRelationType,
    AgentTagLink,
    AgentType,
    AuthorityType,
    MainAgentType,
    MediumType,
    NodeIdentifier,
    NodeNote,
    RefCode,
    RuleConventionType,
    SourcesOfAuthority,
    Structure,
    StructureUnit,
    Tag,
    TagStructure,
    TagVersion,
    TagVersionRelation,
    Topography,
)


class RefCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefCode
        fields = ('country', 'repository_code',)


class AgentIdentifierSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='type.name')

    class Meta:
        model = AgentIdentifier
        fields = ('id', 'identifier', 'type',)


class AgentIdentifierWriteSerializer(serializers.ModelSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=AgentIdentifierType.objects.all())

    class Meta:
        model = AgentIdentifier
        fields = ('id', 'identifier', 'type',)


class AgentNameSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='type.name')

    class Meta:
        model = AgentName
        fields = ('main', 'part', 'description', 'type', 'start_date', 'end_date', 'certainty',)


class AgentNameWriteSerializer(AgentNameSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=AgentNameType.objects.all())


class AgentNoteSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='type.name')

    class Meta:
        model = AgentNote
        fields = ('text', 'type', 'href', 'create_date', 'revise_date',)


class AgentNoteWriteSerializer(AgentNoteSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=AgentNoteType.objects.all())

    class Meta(AgentNoteSerializer.Meta):
        extra_kwargs = {
            'create_date': {
                'default': timezone.now,
            },
        }


class SourcesOfAuthoritySerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='type.name')

    class Meta:
        model = SourcesOfAuthority
        fields = ('id', 'name', 'description', 'type', 'href', 'start_date', 'end_date',)


class SourcesOfAuthorityWriteSerializer(SourcesOfAuthoritySerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=AuthorityType.objects.all())


class TopographySerializer(serializers.ModelSerializer):
    class Meta:
        model = Topography
        fields = (
            'id',
            'name',
            'alt_name',
            'type',
            'main_category',
            'sub_category',
            'reference_code',
            'start_year',
            'end_year',
            'lng',
            'lat',
        )


class AgentPlaceSerializer(serializers.ModelSerializer):
    topography = TopographySerializer()
    type = serializers.CharField(source='type.name')

    class Meta:
        model = AgentPlace
        fields = ('id', 'topography', 'type', 'description', 'start_date', 'end_date')


class AgentPlaceWriteSerializer(AgentPlaceSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=AgentPlaceType.objects.all())


class MainAgentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainAgentType
        fields = ('id', 'name',)


class AgentTypeSerializer(serializers.ModelSerializer):
    main_type = MainAgentTypeSerializer()

    class Meta:
        model = AgentType
        fields = ('id', 'main_type', 'sub_type', 'cpf',)


class RelatedAgentSerializer(serializers.ModelSerializer):
    names = AgentNameSerializer(many=True)
    type = AgentTypeSerializer()

    class Meta:
        model = Agent
        fields = ('id', 'names', 'type',)


class AgentRelationSerializer(serializers.ModelSerializer):
    agent = RelatedAgentSerializer(source='agent_b')
    type = serializers.CharField(source='type.name')

    class Meta:
        model = AgentRelation
        fields = ('type', 'description', 'start_date', 'end_date', 'create_date', 'revise_date', 'agent',)


class AgentRelationWriteSerializer(AgentRelationSerializer):
    agent = serializers.PrimaryKeyRelatedField(source='agent_b', queryset=Agent.objects.all())
    type = serializers.PrimaryKeyRelatedField(queryset=AgentRelationType.objects.all())


class AgentSerializer(serializers.ModelSerializer):
    identifiers = AgentIdentifierSerializer(many=True, required=False)
    names = AgentNameSerializer(many=True, required=False)
    notes = AgentNoteSerializer(many=True, required=False)
    places = AgentPlaceSerializer(source='agentplace_set', many=True, required=False)
    type = AgentTypeSerializer()
    mandates = SourcesOfAuthoritySerializer(many=True, required=False)
    related_agents = AgentRelationSerializer(source='agent_relations_a', many=True, required=False)
    ref_code = RefCodeSerializer()

    class Meta:
        model = Agent
        fields = (
            'id',
            'names',
            'notes',
            'type',
            'ref_code',
            'identifiers',
            'places',
            'mandates',
            'level_of_detail',
            'record_status',
            'script',
            'language',
            'mandates',
            'related_agents',
            'create_date',
            'revise_date',
            'start_date',
            'end_date',
        )


class AgentWriteSerializer(AgentSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=AgentType.objects.all())
    ref_code = serializers.PrimaryKeyRelatedField(queryset=RefCode.objects.all())
    identifiers = AgentIdentifierWriteSerializer(many=True, required=False)
    mandates = SourcesOfAuthorityWriteSerializer(many=True, required=False)
    names = AgentNameWriteSerializer(many=True, required=False)
    notes = AgentNoteWriteSerializer(many=True, required=False)
    places = AgentPlaceWriteSerializer(source='agent_places', many=True, required=False)
    related_agents = AgentRelationWriteSerializer(source='agent_relations_a', many=True, required=False)

    @staticmethod
    def create_identifiers(agent, identifiers_data):
        AgentIdentifier.objects.bulk_create([
            AgentIdentifier(agent=agent, **identifier)
            for identifier in identifiers_data
        ])

    @staticmethod
    def create_mandates(agent, mandates_data):
        mandates = SourcesOfAuthority.objects.bulk_create([
            SourcesOfAuthority(**mandate)
            for mandate in mandates_data
        ])

        agent.mandates.set(mandates)

    @staticmethod
    def create_names(agent, names_data):
        AgentName.objects.bulk_create([
            AgentName(agent=agent, **name)
            for name in names_data
        ])

    @staticmethod
    def create_notes(agent, notes_data):
        AgentNote.objects.bulk_create([
            AgentNote(agent=agent, **note)
            for note in notes_data
        ])

    @staticmethod
    def create_places(agent, places_data):
        for place_data in places_data:
            topography_data = place_data.pop('topography')
            topography_name = topography_data.pop('name')
            topography_type = topography_data.pop('type')
            topography, _ = Topography.objects.get_or_create(
                name=topography_name,
                type=topography_type,
                defaults=topography_data,
            )

            AgentPlace.objects.create(
                agent=agent,
                topography=topography,
                **place_data,
            )

    @staticmethod
    def create_relations(agent, agent_relations):
        AgentRelation.objects.bulk_create([
            AgentRelation(agent_a=agent, **relation)
            for relation in agent_relations
        ])

    @transaction.atomic
    def create(self, validated_data):
        identifiers_data = validated_data.pop('identifiers', [])
        mandates_data = validated_data.pop('mandates', [])
        names_data = validated_data.pop('names', [])
        notes_data = validated_data.pop('notes', [])
        places_data = validated_data.pop('agent_places', [])
        related_agents_data = validated_data.pop('agent_relations_a', [])
        agent = Agent.objects.create(**validated_data)

        self.create_identifiers(agent, identifiers_data)
        self.create_mandates(agent, mandates_data)
        self.create_names(agent, names_data)
        self.create_notes(agent, notes_data)
        self.create_places(agent, places_data)
        self.create_relations(agent, related_agents_data)

        return agent

    @transaction.atomic
    def update(self, instance, validated_data):
        identifiers_data = validated_data.pop('identifiers', None)
        mandates_data = validated_data.pop('mandates', None)
        names_data = validated_data.pop('names', None)
        notes_data = validated_data.pop('notes', None)
        places_data = validated_data.pop('agent_places', None)
        related_agents_data = validated_data.pop('agent_relations_a', None)

        if identifiers_data is not None:
            AgentIdentifier.objects.filter(agent=instance).delete()
            self.create_identifiers(instance, identifiers_data)

        if mandates_data is not None:
            SourcesOfAuthority.objects.filter(agents=instance).delete()
            self.create_mandates(instance, mandates_data)

        if names_data is not None:
            AgentName.objects.filter(agent=instance).delete()
            self.create_names(instance, names_data)

        if notes_data is not None:
            AgentNote.objects.filter(agent=instance).delete()
            for note in notes_data:
                note.setdefault('create_date', timezone.now())
            self.create_notes(instance, notes_data)

        if places_data is not None:
            AgentPlace.objects.filter(agent=instance).delete()
            self.create_places(instance, places_data)

        if related_agents_data is not None:
            AgentRelation.objects.filter(agent_a=instance).delete()
            self.create_relations(instance, related_agents_data)

        return super().update(instance, validated_data)

    def validate_names(self, value):
        for name in value:
            if name.get('start_date') and name.get('start_date') > name.get('end_date'):
                raise serializers.ValidationError(_("end date must occur after start date"))

        if len(value) == 0:
            raise serializers.ValidationError(_("Agents requires at least one name"))

        return value

    def validate(self, data):
        if data.get('start_date') and data.get('start_date') > data.get('end_date'):
            raise serializers.ValidationError(_("end date must occur after start date"))

        return data

    class Meta(AgentSerializer.Meta):
        extra_kwargs = {
            'create_date': {
                'default': timezone.now,
            },
        }


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


class StructureUnitSerializer(serializers.ModelSerializer):
    identifiers = NodeIdentifierSerializer(many=True)
    notes = NodeNoteSerializer(many=True)
    is_leaf_node = serializers.SerializerMethodField()
    is_unit_leaf_node = serializers.SerializerMethodField()

    def get_is_unit_leaf_node(self, obj):
        return obj.is_leaf_node()

    def get_is_leaf_node(self, obj):
        archive_id = self.context.get('archive')
        archive_structure_id = self.context.get('archive_structure')
        structure_id = self.context.get('structure')

        if archive_structure_id is not None:
            archive = TagStructure.objects.get(pk=archive_structure_id)
        elif archive_id is not None:
            archive_qs = TagStructure.objects.filter(tag__versions=archive_id)
            if structure_id is not None:
                archive_qs = archive_qs.filter(structure=structure_id)

            archive = archive_qs.get()
        else:
            return obj.is_leaf_node()

        archive_descendants = archive.get_descendants().filter(structure_unit=obj)

        return obj.is_leaf_node() and not archive_descendants.exists()

    class Meta:
        model = StructureUnit
        fields = (
            'id', 'parent', 'name', 'type', 'description',
            'reference_code', 'start_date', 'end_date', 'is_leaf_node',
            'is_unit_leaf_node', 'structure', 'identifiers', 'notes',
        )


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
    type = serializers.CharField(source='type.name')

    class Meta:
        model = AgentTagLink
        fields = ('archive', 'type', 'description', 'start_date', 'end_date',)


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
