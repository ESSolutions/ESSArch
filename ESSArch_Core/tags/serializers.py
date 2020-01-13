import uuid

import elasticsearch
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from django.utils.translation import ugettext as _
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from ESSArch_Core.agents.models import (
    Agent,
    AgentTagLink,
    AgentTagLinkRelationType,
)
from ESSArch_Core.agents.serializers import (
    AgentNameSerializer,
    AgentSerializer,
    AgentTagLinkRelationTypeSerializer,
)
from ESSArch_Core.api.validators import StartDateEndDateValidator
from ESSArch_Core.auth.fields import CurrentUsernameDefault
from ESSArch_Core.auth.models import GroupGenericObjects
from ESSArch_Core.auth.serializers import GroupSerializer, UserSerializer
from ESSArch_Core.configuration.models import EventType
from ESSArch_Core.ip.models import EventIP, InformationPackage
from ESSArch_Core.profiles.models import SubmissionAgreement
from ESSArch_Core.profiles.serializers import SubmissionAgreementSerializer
from ESSArch_Core.tags.documents import (
    Archive,
    Component,
    File,
    StructureUnitDocument,
)
from ESSArch_Core.tags.models import (
    Delivery,
    DeliveryType,
    Location,
    LocationFunctionType,
    LocationLevelType,
    MediumType,
    MetricType,
    NodeIdentifier,
    NodeIdentifierType,
    NodeNote,
    NodeNoteType,
    NodeRelationType,
    RuleConventionType,
    Search,
    Structure,
    StructureRelation,
    StructureRelationType,
    StructureType,
    StructureUnit,
    StructureUnitRelation,
    StructureUnitType,
    Tag,
    TagStructure,
    TagVersion,
    TagVersionRelation,
    TagVersionType,
    Transfer,
)

PUBLISHED_STRUCTURE_CHANGE_ERROR = _('Published structures cannot be changed')
NON_EDITABLE_STRUCTURE_CHANGE_ERROR = _('{} cannot be changed')
STRUCTURE_INSTANCE_RELATION_ERROR = _('Cannot add relations to structure instances')


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
    def validate_history(self, value):
        if value:
            try:
                existing = NodeNoteType.objects.get(history=True)
                if existing != self.instance:
                    raise serializers.ValidationError(
                        NodeNoteType.unique_history_error,
                    )
            except NodeNoteType.DoesNotExist:
                pass

        return value

    class Meta:
        model = NodeNoteType
        fields = ('id', 'name', 'history',)


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


class StructureRelationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StructureRelationType
        fields = ('id', 'name',)


class RelatedStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Structure
        fields = ('id', 'name',)


class StructureRelationSerializer(serializers.ModelSerializer):
    structure = RelatedStructureSerializer(source='structure_b')
    type = StructureRelationTypeSerializer()

    class Meta:
        model = StructureRelation
        fields = ('id', 'type', 'description', 'start_date', 'end_date',
                  'create_date', 'revise_date', 'structure',)


class StructureRelationWriteSerializer(StructureRelationSerializer):
    structure = serializers.PrimaryKeyRelatedField(
        source='structure_b', queryset=Structure.objects.filter(is_template=True)
    )
    type = serializers.PrimaryKeyRelatedField(queryset=StructureRelationType.objects.all())


class StructureSerializer(serializers.ModelSerializer):
    type = StructureTypeSerializer()
    rule_convention_type = RuleConventionTypeSerializer()
    specification = serializers.JSONField(default={})
    created_by = UserSerializer(read_only=True, default=serializers.CurrentUserDefault())
    revised_by = UserSerializer(read_only=True, default=serializers.CurrentUserDefault())
    related_structures = StructureRelationSerializer(
        source='structure_relations_a', many=True, required=False
    )

    class Meta:
        model = Structure
        fields = ('id', 'name', 'type', 'description', 'template', 'is_template', 'version',
                  'create_date', 'revise_date', 'start_date', 'end_date', 'specification',
                  'rule_convention_type', 'created_by', 'revised_by', 'published', 'published_date',
                  'related_structures', 'is_editable',)
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
    related_structures = StructureRelationWriteSerializer(
        source='structure_relations_a', many=True, required=False
    )

    def validate(self, data):
        if set(data.keys()) == {'structure_relations_a'}:
            if not self.instance.is_template:
                raise serializers.ValidationError(STRUCTURE_INSTANCE_RELATION_ERROR)
            return data

        version = data.get('version')
        version_link = data.get('version_link')

        version_fields = ', '.join(['version', 'version_link'])
        version_unique_together_error_msg = UniqueTogetherValidator.message.format(field_names=version_fields)
        version_exists = Structure.objects.filter(version=version, version_link=version_link).exists()

        if self.instance:
            if self.instance.published:
                raise serializers.ValidationError(PUBLISHED_STRUCTURE_CHANGE_ERROR)

            if not self.instance.is_editable:
                raise serializers.ValidationError(
                    NON_EDITABLE_STRUCTURE_CHANGE_ERROR.format(self.instance.name)
                )

            if (version is not None or version_link is not None) and self.instance.version != version:
                version = version or self.instance.version
                version_link = version_link or self.instance.version_link
                if Structure.objects.filter(version=version, version_link=version_link).exists():
                    raise serializers.ValidationError(version_unique_together_error_msg, code='unique')
        else:
            if version_exists:
                raise serializers.ValidationError(version_unique_together_error_msg, code='unique')

        return data

    @staticmethod
    def create_relations(structure, structure_relations):
        for relation in structure_relations:
            other_structure = relation.pop('structure_b')
            relation_type = relation.pop('type')
            structure.relate_to(other_structure, relation_type, **relation)

    @transaction.atomic
    def create(self, validated_data):
        validated_data['is_template'] = True
        validated_data['created_by'] = self.context['request'].user
        validated_data['revised_by'] = self.context['request'].user
        related_structures_data = validated_data.pop('structure_relations_a', [])
        structure = super().create(validated_data)

        self.create_relations(structure, related_structures_data)
        return structure

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data['revised_by'] = self.context['request'].user
        related_structures_data = validated_data.pop('structure_relations_a', None)

        if related_structures_data is not None:
            StructureRelation.objects.filter(Q(structure_a=instance) | Q(structure_b=instance)).delete()
            self.create_relations(instance, related_structures_data)

        return super().update(instance, validated_data)

    class Meta(StructureSerializer.Meta):
        fields = StructureSerializer.Meta.fields + ('version_link',)
        validators = [
            StartDateEndDateValidator(
                start_date='start_date',
                end_date='end_date',
            ),
        ]
        extra_kwargs = {
            'is_template': {'read_only': True},
            'template': {'read_only': True},
            'version': {
                'default': '1.0',
            }
        }


class RelatedStructureUnitSerializer(serializers.ModelSerializer):
    structure = StructureSerializer(read_only=True)
    archive = serializers.SerializerMethodField(read_only=True)

    def get_archive(self, obj):
        tag_structure = obj.structure.tagstructure_set.filter(
            tag__current_version__elastic_index='archive'
        ).first()

        if tag_structure is not None:
            return tag_structure.tag.current_version.pk

        return None

    class Meta:
        model = StructureUnit
        fields = ('id', 'name', 'structure', 'archive')


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
    is_tag_leaf_node = serializers.SerializerMethodField()
    is_unit_leaf_node = serializers.SerializerMethodField()
    related_structure_units = StructureUnitRelationSerializer(
        source='structure_unit_relations_a', many=True, required=False
    )

    @staticmethod
    def get_is_unit_leaf_node(obj):
        return obj.is_leaf_node()

    @staticmethod
    def get_is_tag_leaf_node(obj):
        # TODO: Make this a recursive check and add a separate field
        # indicating if this unit have any direct tag children

        archive_descendants = obj.structure.tagstructure_set.annotate(
            versions_exists=Exists(TagVersion.objects.filter(tag=OuterRef('tag')))
        ).filter(structure_unit=obj, versions_exists=True)
        return not archive_descendants.exists()

    def get_is_leaf_node(self, obj):
        return self.get_is_unit_leaf_node(obj) and self.get_is_tag_leaf_node(obj)

    class Meta:
        model = StructureUnit
        fields = (
            'id', 'parent', 'name', 'type', 'description',
            'reference_code', 'start_date', 'end_date', 'is_leaf_node',
            'is_tag_leaf_node', 'is_unit_leaf_node', 'structure',
            'identifiers', 'notes', 'related_structure_units',
        )


class StructureUnitDetailSerializer(StructureUnitSerializer):
    archive = serializers.SerializerMethodField(read_only=True)

    def get_archive(self, obj):
        tag_structure = obj.structure.tagstructure_set.filter(
            tag__current_version__elastic_index='archive'
        ).first()

        if tag_structure is not None:
            return tag_structure.tag.current_version.pk

        return None

    class Meta(StructureUnitSerializer.Meta):
        fields = StructureUnitSerializer.Meta.fields + ('archive',)


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

                parent = copied['parent']

                if parent is not None:
                    has_tags = parent.structure.tagstructure_set.annotate(
                        versions_exists=Exists(TagVersion.objects.filter(tag=OuterRef('tag')))
                    ).filter(structure_unit=parent, versions_exists=True)

                    if has_tags:
                        raise serializers.ValidationError(
                            _('Units cannot be placed in a unit with tags').format(structure_type)
                        )

                copied.pop('parent', None)

            copied.pop('structure_unit_relations_a', None)

            # are we editing?
            if len(copied.keys()) > 0:
                if not structure_type.editable_instances:
                    raise serializers.ValidationError(
                        _('Units in instances of type {} cannot be edited').format(structure_type)
                    )

        if self.instance and self.instance.structure.is_template:
            if self.instance.structure.published:
                raise serializers.ValidationError(PUBLISHED_STRUCTURE_CHANGE_ERROR)
            if not self.instance.structure.is_editable:
                raise serializers.ValidationError(NON_EDITABLE_STRUCTURE_CHANGE_ERROR)

        unit_type = data.get('type')

        if structure is not None and unit_type is not None:
            if structure.is_template:
                if structure.published:
                    raise serializers.ValidationError(PUBLISHED_STRUCTURE_CHANGE_ERROR)
                if not structure.is_editable:
                    raise serializers.ValidationError(NON_EDITABLE_STRUCTURE_CHANGE_ERROR)

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
    type = AgentTagLinkRelationTypeSerializer()

    class Meta:
        model = AgentTagLink
        fields = ('agent', 'type', 'start_date', 'end_date', 'description',)


class TagVersionTypeSerializer(serializers.ModelSerializer):
    custom_fields_template = serializers.JSONField(required=False)

    class Meta:
        model = TagVersionType
        fields = ('pk', 'name', 'archive_type', 'information_package_type', 'custom_fields_template')


class MetricTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricType
        fields = ('id', 'name',)


class LocationLevelTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationLevelType
        fields = ('id', 'name',)


class LocationFunctionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationFunctionType
        fields = ('id', 'name',)


class LocationSerializer(serializers.ModelSerializer):
    metric = MetricTypeSerializer()
    level_type = LocationLevelTypeSerializer()
    function = LocationFunctionTypeSerializer()

    class Meta:
        model = Location
        fields = ('id', 'name', 'parent', 'level_type', 'function', 'metric', 'capacity',)


class LocationWriteSerializer(LocationSerializer):
    metric = serializers.PrimaryKeyRelatedField(
        allow_null=True, required=False, default=None,
        queryset=MetricType.objects.all(),
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
        fields = ('name', 'parent', 'level_type', 'function', 'metric', 'capacity')


class TagVersionInformationPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InformationPackage
        fields = ('id', 'object_identifier_value', 'label',)


class TagVersionNestedSerializer(serializers.ModelSerializer):
    _id = serializers.UUIDField(source='pk')
    _index = serializers.CharField(source='elastic_index')
    is_leaf_node = serializers.SerializerMethodField()
    _source = serializers.SerializerMethodField()
    masked_fields = serializers.SerializerMethodField()
    related_tags = TagVersionRelationSerializer(source='tag_version_relations_a', many=True)
    medium_type = MediumTypeSerializer()
    notes = NodeNoteSerializer(many=True)
    identifiers = NodeIdentifierSerializer(many=True)
    agents = TagVersionAgentTagLinkSerializer(source='agent_links', many=True)
    type = TagVersionTypeSerializer()
    metric = MetricTypeSerializer()
    location = LocationSerializer()
    custom_fields = serializers.JSONField()
    information_package = TagVersionInformationPackageSerializer(
        source='tag.information_package', read_only=True,
    )

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
        custom_fields = obj.custom_fields

        hidden_fields = ['restrictions']
        masked_fields = self.get_masked_fields(obj)

        for field in custom_fields.keys():
            if field in masked_fields:
                custom_fields[field] = ''
            if field in hidden_fields:
                custom_fields.pop(field)
        return custom_fields

    class Meta:
        model = TagVersion
        fields = (
            '_id', '_index', 'name', 'type', 'create_date', 'revise_date',
            'import_date', 'start_date', 'related_tags', 'notes', 'end_date',
            'is_leaf_node', '_source', 'masked_fields',
            'medium_type', 'identifiers', 'agents', 'description', 'reference_code',
            'custom_fields', 'metric', 'location', 'capacity', 'information_package',
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
    root = serializers.SerializerMethodField()
    structure_unit = serializers.SerializerMethodField()
    organization = serializers.SerializerMethodField()

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

    def get_organization(self, obj):
        try:
            ctype = ContentType.objects.get_for_model(obj)
            group = GroupGenericObjects.objects.get(object_id=obj.pk, content_type=ctype).group
            serializer = GroupSerializer(instance=group)
            return serializer.data
        except GroupGenericObjects.DoesNotExist:
            return None

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
        fields = TagVersionNestedSerializer.Meta.fields + (
            'structure_unit', 'structures', 'parent', 'organization', 'root',
        )


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
        fields = (
            'id', 'name', 'type', 'description', 'submission_agreement',
            'producer_organization', 'reference_code',
        )


class DeliveryWriteSerializer(DeliverySerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=DeliveryType.objects.all())
    submission_agreement = serializers.PrimaryKeyRelatedField(
        queryset=SubmissionAgreement.objects.filter(published=True), default=None, allow_null=True)
    producer_organization = serializers.PrimaryKeyRelatedField(
        queryset=Agent.objects.all(), default=None, allow_null=True,
    )

    def create(self, validated_data):
        obj = super().create(validated_data)

        org = self.context['request'].user.user_profile.current_organization
        org.add_object(obj)

        event_type = EventType.objects.get(eventType='20300')
        EventIP.objects.create(
            delivery=obj,
            eventType=event_type,
        )
        return obj


class TransferSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        obj = super().create(validated_data)

        org = self.context['request'].user.user_profile.current_organization
        org.add_object(obj)

        return obj

    class Meta:
        model = Transfer
        fields = (
            'id', 'name', 'delivery', 'submitter_organization', 'submitter_organization_main_address',
            'submitter_individual_name', 'submitter_individual_phone', 'submitter_individual_email',
            'description',
        )


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


class ComponentWriteSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField(required=False)
    type = serializers.PrimaryKeyRelatedField(queryset=TagVersionType.objects.filter(archive_type=False))
    reference_code = serializers.CharField()
    information_package = serializers.PrimaryKeyRelatedField(
        default=None,
        queryset=InformationPackage.objects.filter(archived=True),
    )
    index = serializers.ChoiceField(choices=['component', 'document'])
    parent = serializers.PrimaryKeyRelatedField(required=False, queryset=TagVersion.objects.all())
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all(), allow_null=True)
    structure = serializers.PrimaryKeyRelatedField(
        required=False, queryset=Structure.objects.filter(is_template=False))
    structure_unit = serializers.PrimaryKeyRelatedField(
        required=False,
        queryset=StructureUnit.objects.filter(structure__is_template=False),
    )
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    custom_fields = serializers.JSONField(required=False)
    notes = NodeNoteWriteSerializer(many=True, required=False)
    identifiers = NodeIdentifierWriteSerializer(many=True, required=False)

    @staticmethod
    def create_notes(tag_version, notes_data):
        NodeNote.objects.bulk_create([
            NodeNote(tag_version=tag_version, **note)
            for note in notes_data
        ])

    @staticmethod
    def create_identifiers(tag_version, identifiers_data):
        NodeIdentifier.objects.bulk_create([
            NodeIdentifier(tag_version=tag_version, **identifier)
            for identifier in identifiers_data
        ])

    def create(self, validated_data):
        with transaction.atomic():
            structure_unit = validated_data.pop('structure_unit', None)
            parent = validated_data.pop('parent', None)
            structure = validated_data.pop('structure', None)
            notes_data = validated_data.pop('notes', [])
            identifiers_data = validated_data.pop('identifiers', [])
            information_package = validated_data.pop('information_package', None)
            index = validated_data.pop('index')

            tag = Tag.objects.create(information_package=information_package)
            tag_structure = TagStructure(tag=tag)

            if structure_unit is not None:
                tag_structure.structure_unit = structure_unit
                tag_structure.structure = structure_unit.structure

                archive_structure = TagStructure.objects.filter(structure=structure_unit.structure).first().get_root()
                tag_structure.parent = archive_structure

                tag_structure.save()

            else:
                if structure is None:
                    parent_structure = parent.get_active_structure()
                else:
                    parent_structure = parent.get_structures(structure).get()

                tag_structure.parent = parent_structure
                tag_structure.structure = parent_structure.structure

            tag_structure.save()

            tag_version = TagVersion.objects.create(
                tag=tag, elastic_index=index, **validated_data,
            )
            tag.current_version = tag_version
            tag.save()

            for agent_link in AgentTagLink.objects.filter(tag=tag_version):
                AgentTagLink.objects.create(tag=tag_version, agent=agent_link.agent, type=agent_link.type)

            tag_structure.refresh_from_db()
            if structure_unit is None:
                structure_unit = tag_structure.get_ancestors(
                    include_self=True
                ).filter(structure_unit__isnull=False).get().structure_unit
            related_units = structure_unit.related_structure_units.filter(
                structure__is_template=False
            ).exclude(
                structure=tag_structure.structure
            )

            for related in related_units:
                new_unit = related if tag_structure.structure_unit is not None else None
                tag_structure.copy_to_new_structure(related.structure, new_unit=new_unit)

            self.create_identifiers(self, identifiers_data)
            self.create_notes(self, notes_data)

        doc = Component.from_obj(tag_version)
        doc.save()

        return tag

    def update(self, instance, validated_data):
        structure_unit = validated_data.pop('structure_unit', None)
        parent = validated_data.pop('parent', None)
        structure = validated_data.pop('structure', None)
        notes_data = validated_data.pop('notes', None)
        identifiers_data = validated_data.pop('identifiers', None)
        information_package = validated_data.pop('information_package', None)
        validated_data.pop('index', None)

        if identifiers_data is not None:
            NodeIdentifier.objects.filter(tag_version=instance).delete()
            self.create_identifiers(instance, identifiers_data)

        if notes_data is not None:
            NodeNote.objects.filter(tag_version=instance).delete()
            for note in notes_data:
                note.setdefault('create_date', timezone.now())
            self.create_notes(instance, notes_data)

        if structure is not None:
            tag = instance.tag

            if structure_unit is not None:
                archive_structure = structure.tagstructure_set.first().get_root()
                parent = archive_structure

            elif parent is not None:
                parent_structure = parent.get_structures(structure).get()
                parent = parent_structure
                structure_unit = None

            TagStructure.objects.update_or_create(tag=tag, structure=structure, defaults={
                'parent': parent,
                'structure_unit': structure_unit,
            })

        instance.tag.information_package = information_package
        instance.tag.save()
        TagVersion.objects.filter(pk=instance.pk).update(**validated_data)
        instance.refresh_from_db()

        if instance.elastic_index == 'component':
            doc = Component.from_obj(instance)
        elif instance.elastic_index == 'document':
            doc = File.from_obj(instance)

        doc.save()

        return instance

    def validate_parent(self, value):
        if not self.instance:
            return value

        if value == self.instance:
            raise serializers.ValidationError(_("Cannot be parent to itself"))

        return value

    def validate_structure_unit(self, value):
        if not value.is_leaf_node():
            raise serializers.ValidationError(_("Must be a leaf unit"))

        return value

    def validate(self, data):
        if not self.instance:
            if 'parent' not in data and 'structure_unit' not in data:
                raise serializers.ValidationError('parent or structure_unit required')

            if 'structure_unit' not in data and data['parent'].type.archive_type:
                raise serializers.ValidationError('structure_unit required when parent is an archive')

        if self.instance:
            structure_unit = data.get('structure_unit', None)
            parent = data.get('parent', None)

            if structure_unit is not None and parent is not None and not parent.type.archive_type:
                raise serializers.ValidationError('structure_unit not allowed when parent is not an archive')

        if data.get('information_package') is not None and not data['type'].information_package_type:
            raise serializers.ValidationError('information package can only be set on information package nodes')

        if data.get('start_date') and data.get('end_date') and \
           data.get('start_date') > data.get('end_date'):

            raise serializers.ValidationError(_("end date must occur after start date"))

        return data


class ArchiveWriteSerializer(serializers.Serializer):
    name = serializers.CharField()
    type = serializers.PrimaryKeyRelatedField(queryset=TagVersionType.objects.filter(archive_type=True))
    structures = serializers.PrimaryKeyRelatedField(
        queryset=Structure.objects.filter(is_template=True, published=True),
        many=True,
    )
    archive_creator = serializers.PrimaryKeyRelatedField(queryset=Agent.objects.all())
    description = serializers.CharField(required=False)
    reference_code = serializers.CharField(required=False, allow_blank=True)
    use_uuid_as_refcode = serializers.BooleanField(default=False)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    custom_fields = serializers.JSONField(required=False)
    notes = NodeNoteWriteSerializer(many=True, required=False)
    identifiers = NodeIdentifierWriteSerializer(many=True, required=False)

    @staticmethod
    def create_notes(tag_version, notes_data):
        NodeNote.objects.bulk_create([
            NodeNote(tag_version=tag_version, **note)
            for note in notes_data
        ])

    @staticmethod
    def create_identifiers(tag_version, identifiers_data):
        NodeIdentifier.objects.bulk_create([
            NodeIdentifier(tag_version=tag_version, **identifier)
            for identifier in identifiers_data
        ])

    def create(self, validated_data):
        with transaction.atomic():
            agent = validated_data.pop('archive_creator')
            structures = validated_data.pop('structures')
            notes_data = validated_data.pop('notes', [])
            identifiers_data = validated_data.pop('identifiers', [])
            use_uuid_as_refcode = validated_data.pop('use_uuid_as_refcode', False)
            tag_version_id = uuid.uuid4()

            if use_uuid_as_refcode:
                validated_data['reference_code'] = str(tag_version_id)

            tag = Tag.objects.create()
            tag_version = TagVersion.objects.create(
                pk=tag_version_id, tag=tag, elastic_index='archive',
                **validated_data,
            )
            tag.current_version = tag_version
            tag.save()

            for structure in structures:
                structure_instance, _ = structure.create_template_instance(tag)
                for instance_unit in structure_instance.units.all():
                    StructureUnitDocument.from_obj(instance_unit).save()

            org = self.context['request'].user.user_profile.current_organization
            org.add_object(tag)
            org.add_object(tag_version)

            tag_link_type, _ = AgentTagLinkRelationType.objects.get_or_create(
                creator=True, defaults={'name': 'creator'}
            )
            AgentTagLink.objects.create(agent=agent, tag=tag_version, type=tag_link_type)
            self.create_identifiers(self, identifiers_data)
            self.create_notes(self, notes_data)

        doc = Archive.from_obj(tag_version)
        doc.save()

        return tag

    def update(self, instance, validated_data):
        structures = validated_data.pop('structures', [])
        notes_data = validated_data.pop('notes', None)
        identifiers_data = validated_data.pop('identifiers', None)

        if identifiers_data is not None:
            NodeIdentifier.objects.filter(tag_version=instance).delete()
            self.create_identifiers(instance, identifiers_data)

        if notes_data is not None:
            NodeNote.objects.filter(tag_version=instance).delete()
            for note in notes_data:
                note.setdefault('create_date', timezone.now())
            self.create_notes(instance, notes_data)

        with transaction.atomic():
            for structure in structures:
                if not TagStructure.objects.filter(tag=instance.tag, structure__template=structure).exists():
                    structure_instance, _ = structure.create_template_instance(instance.tag)
                    for instance_unit in structure_instance.units.all():
                        StructureUnitDocument.from_obj(instance_unit).save()

            TagVersion.objects.filter(pk=instance.pk).update(**validated_data)
            instance.refresh_from_db()

        doc = Archive.from_obj(instance)
        doc.save()

        return instance

    def validate_structures(self, structures):
        if not len(structures):
            raise serializers.ValidationError(_("At least one structure is required"))

        if self.instance:
            existing_structures = Structure.objects.filter(instances__tagstructure__tag=self.instance.tag)

            for existing_structure in existing_structures:
                structure_instance = Structure.objects.get(
                    template=existing_structure, tagstructure__tag=self.instance.tag,
                )
                if existing_structure not in structures:
                    empty_structure = not structure_instance.tagstructure_set.filter(
                        tag__versions__type__archive_type=False
                    ).exists()
                    if not empty_structure:
                        raise serializers.ValidationError(_("Non-empty structures cannot be deleted from archives"))
                    else:
                        TagStructure.objects.filter(structure=structure_instance).delete()
                        structure_instance.delete()

        return structures

    def validate(self, data):
        if data.get('start_date') and data.get('end_date') and \
           data.get('start_date') > data.get('end_date'):

            raise serializers.ValidationError(_("end date must occur after start date"))

        if not self.instance and not data.get('reference_code') and not data.get('use_uuid_as_refcode'):
            raise serializers.ValidationError(_("either reference_code or use_uuid_as_refcode must be set"))

        return data


class StoredSearchSerializer(serializers.ModelSerializer):
    user = serializers.CharField(read_only=True, default=CurrentUsernameDefault())
    query = serializers.JSONField()

    def create(self, validated_data):
        if 'user' not in validated_data:
            validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    class Meta:
        model = Search
        fields = ('id', 'name', 'user', 'query',)
