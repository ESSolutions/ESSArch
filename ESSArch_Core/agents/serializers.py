from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from ESSArch_Core.agents.models import (
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
    AgentTagLinkRelationType,
    AgentType,
    AuthorityType,
    MainAgentType,
    RefCode,
    SourcesOfAuthority,
    Topography,
)
from ESSArch_Core.api.validators import StartDateEndDateValidator


class RefCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefCode
        fields = ('id', 'country', 'repository_code',)


class AgentIdentifierTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentIdentifierType
        fields = ('id', 'name')


class AgentIdentifierSerializer(serializers.ModelSerializer):
    type = AgentIdentifierTypeSerializer()

    class Meta:
        model = AgentIdentifier
        fields = ('id', 'identifier', 'type',)


class AgentIdentifierWriteSerializer(serializers.ModelSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=AgentIdentifierType.objects.all())

    class Meta:
        model = AgentIdentifier
        fields = ('id', 'identifier', 'type',)


class AgentNameTypeSerializer(serializers.ModelSerializer):
    def validate_authority(self, value):
        if value:
            try:
                existing = AgentNameType.objects.get(authority=True)
                if existing != self.instance:
                    raise serializers.ValidationError(
                        AgentNameType.unique_authority_error,
                    )
            except AgentNameType.DoesNotExist:
                pass

        return value

    class Meta:
        model = AgentNameType
        fields = ('id', 'name', 'authority',)


class AgentNameSerializer(serializers.ModelSerializer):
    type = AgentNameTypeSerializer()

    class Meta:
        model = AgentName
        fields = ('id', 'main', 'part', 'description', 'type', 'start_date', 'end_date', 'certainty',)


class AgentNameWriteSerializer(AgentNameSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=AgentNameType.objects.all())


class AgentNoteTypeSerializer(serializers.ModelSerializer):
    def validate_history(self, value):
        if value:
            try:
                existing = AgentNoteType.objects.get(history=True)
                if existing != self.instance:
                    raise serializers.ValidationError(
                        AgentNoteType.unique_history_error,
                    )
            except AgentNoteType.DoesNotExist:
                pass

        return value

    class Meta:
        model = AgentNoteType
        fields = ('id', 'name', 'history',)


class AgentNoteSerializer(serializers.ModelSerializer):
    type = AgentNoteTypeSerializer()

    class Meta:
        model = AgentNote
        fields = ('id', 'text', 'type', 'href', 'create_date', 'revise_date',)


class AgentNoteWriteSerializer(AgentNoteSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=AgentNoteType.objects.all())

    class Meta(AgentNoteSerializer.Meta):
        extra_kwargs = {
            'create_date': {
                'default': timezone.now,
            },
        }


class AuthorityTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorityType
        fields = ('id', 'name')


class SourcesOfAuthoritySerializer(serializers.ModelSerializer):
    type = AuthorityTypeSerializer()

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


class AgentPlaceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentPlaceType
        fields = ('id', 'name')


class AgentPlaceSerializer(serializers.ModelSerializer):
    topography = TopographySerializer()
    type = AgentPlaceTypeSerializer()

    class Meta:
        model = AgentPlace
        fields = ('id', 'topography', 'type', 'description', 'start_date', 'end_date')


class AgentPlaceWriteSerializer(AgentPlaceSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=AgentPlaceType.objects.all())
    topography = TopographySerializer(validators=[])


class AgentTagLinkRelationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentTagLinkRelationType
        fields = ('id', 'name',)


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
        fields = ('id', 'names', 'type', 'start_date', 'end_date',)


class AgentRelationTypeMirroredSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRelationType
        fields = ('id', 'name')


class AgentRelationTypeSerializer(serializers.ModelSerializer):
    mirrored_type = AgentRelationTypeMirroredSerializer()

    class Meta:
        model = AgentRelationType
        fields = ('id', 'name', 'mirrored_type',)


class AgentRelationSerializer(serializers.ModelSerializer):
    agent = RelatedAgentSerializer(source='agent_b')
    type = AgentRelationTypeSerializer()

    class Meta:
        model = AgentRelation
        fields = ('id', 'type', 'description', 'start_date', 'end_date', 'create_date', 'revise_date', 'agent',)


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
        relations = set()
        for relation in agent_relations:
            if relation['agent_b'].pk == agent.pk:
                raise serializers.ValidationError(_("Relation to self cannot be created"))
            agent_b = relation.pop('agent_b')
            rel_type = relation.pop('type')

            rel = (agent_b.pk, rel_type.pk)
            if rel in relations:
                raise serializers.ValidationError(_("Same relation cannot be created twice"))

            relations.add(rel)

            AgentRelation.objects.get_or_create(
                agent_a=agent,
                agent_b=agent_b,
                type=rel_type,
                defaults=relation
            )

            AgentRelation.objects.get_or_create(
                agent_a=agent_b,
                agent_b=agent,
                type=rel_type.mirrored_type or rel_type,
                defaults=relation
            )

    @transaction.atomic
    def create(self, validated_data):
        identifiers_data = validated_data.pop('identifiers', [])
        mandates_data = validated_data.pop('mandates', [])
        names_data = validated_data.pop('names', [])
        notes_data = validated_data.pop('notes', [])
        places_data = validated_data.pop('agent_places', [])
        related_agents_data = validated_data.pop('agent_relations_a', [])
        agent = Agent.objects.create(**validated_data)

        org = self.context['request'].user.user_profile.current_organization
        org.add_object(agent)

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
            AgentRelation.objects.filter(Q(agent_a=instance) | Q(agent_b=instance)).delete()
            self.create_relations(instance, related_agents_data)

        return super().update(instance, validated_data)

    def validate_names(self, value):
        for name in value:
            StartDateEndDateValidator('start_date', 'end_date')(name)

        if len(value) == 0:
            raise serializers.ValidationError(_("Agents requires at least one name"))

        return value

    class Meta(AgentSerializer.Meta):
        extra_kwargs = {
            'create_date': {
                'default': timezone.now,
            },
        }
        validators = [
            StartDateEndDateValidator(
                start_date='start_date',
                end_date='end_date',
            )
        ]
