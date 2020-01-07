import logging
import uuid

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, OuterRef, Subquery
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from elasticsearch_dsl.connections import get_connection
from mptt.managers import TreeManager
from mptt.models import MPTTModel, TreeForeignKey

from ESSArch_Core.agents.models import Agent
from ESSArch_Core.fields import JSONField
from ESSArch_Core.managers import OrganizationManager
from ESSArch_Core.profiles.models import SubmissionAgreement

User = get_user_model()
logger = logging.getLogger('essarch.tags')


class NodeIdentifier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identifier = models.TextField(_('identifier'), blank=False)
    tag_version = models.ForeignKey(
        'tags.TagVersion',
        on_delete=models.CASCADE,
        null=True,
        related_name='identifiers',
        verbose_name=_('tag version')
    )
    structure_unit = models.ForeignKey(
        'tags.StructureUnit',
        on_delete=models.CASCADE,
        null=True,
        related_name='identifiers',
        verbose_name=_('structure unit')
    )
    type = models.ForeignKey('tags.NodeIdentifierType', on_delete=models.PROTECT, null=False, verbose_name=_('type'))


class NodeIdentifierType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('node identifier type')
        verbose_name_plural = _('node identifier types')


class NodeNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tag_version = models.ForeignKey(
        'tags.TagVersion',
        on_delete=models.CASCADE,
        null=True,
        related_name='notes',
        verbose_name=_('tag version')
    )
    structure_unit = models.ForeignKey(
        'tags.StructureUnit',
        on_delete=models.CASCADE,
        null=True,
        related_name='notes',
        verbose_name=_('structure unit')
    )
    type = models.ForeignKey('tags.NodeNoteType', on_delete=models.PROTECT, null=False, verbose_name=_('type'))
    text = models.TextField(_('text'), blank=False)
    href = models.TextField(_('href'), blank=True)
    create_date = models.DateTimeField(_('create date'), null=False)
    revise_date = models.DateTimeField(_('revise date'), null=True)


class NodeNoteType(models.Model):
    unique_history_error = _('Only 1 note type can be set as history at a time')

    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)
    history = models.BooleanField(_('history'), default=False)

    def clean(self):
        if self.history:
            try:
                existing = NodeNoteType.objects.get(history=True)
                if existing != self:
                    raise ValidationError(
                        self.unique_history_error,
                        code='invalid',
                    )
            except NodeNoteType.DoesNotExist:
                pass

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('node note type')
        verbose_name_plural = _('node note types')


class NodeRelationType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)
    mirrored_type = models.ForeignKey(
        'self', on_delete=models.PROTECT, blank=True,
        null=True, verbose_name=_('mirrored type'),
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('node relation type')
        verbose_name_plural = _('node relation types')


class StructureType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)
    instance_name = models.CharField(_('instance name'), max_length=255, blank=True)
    editable_instances = models.BooleanField(_('editable instances'), default=False)
    editable_instance_relations = models.BooleanField(_('editable instance relations'), default=False)
    movable_instance_units = models.BooleanField(_('movable instance units'), default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('structure type')
        verbose_name_plural = _('structure types')


class StructureRelationType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)
    mirrored_type = models.ForeignKey(
        'self', on_delete=models.PROTECT, blank=True,
        null=True, verbose_name=_('mirrored type'),
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('structure relation type')
        verbose_name_plural = _('structure relation types')


class StructureRelation(models.Model):
    structure_a = models.ForeignKey(
        'tags.Structure',
        on_delete=models.CASCADE,
        related_name='structure_relations_a',
        limit_choices_to={'is_template': True},
    )
    structure_b = models.ForeignKey(
        'tags.Structure',
        on_delete=models.CASCADE,
        related_name='structure_relations_b',
        limit_choices_to={'is_template': True},
    )
    type = models.ForeignKey('tags.StructureRelationType', on_delete=models.PROTECT, null=False)
    description = models.TextField(_('description'), blank=True)
    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)
    create_date = models.DateTimeField(_('create date'), default=timezone.now)
    revise_date = models.DateTimeField(_('revise date'), auto_now=True)

    class Meta:
        unique_together = ('structure_a', 'structure_b', 'type')  # Avoid duplicates within same type


class RuleConventionType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name


class Structure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=False, db_index=True)
    description = models.TextField(blank=True)
    type = models.ForeignKey(StructureType, on_delete=models.PROTECT)
    template = models.ForeignKey(
        'self', on_delete=models.PROTECT, null=True,
        limit_choices_to={'is_template': True}, related_name='instances', verbose_name=_('template'),
    )
    is_editable = models.BooleanField(_('is editable'), default=True)
    is_template = models.BooleanField(_('is template'))
    published = models.BooleanField(_('published'), default=False)
    published_date = models.DateTimeField(null=True, db_index=True)
    version = models.CharField(max_length=255, blank=False, default='1.0')
    version_link = models.UUIDField(default=uuid.uuid4, null=False)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name='created_structures')
    revised_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name='revised_structures')
    create_date = models.DateTimeField(default=timezone.now, null=True)
    revise_date = models.DateTimeField(auto_now=True)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    specification = JSONField(default={})
    rule_convention_type = models.ForeignKey('tags.RuleConventionType', on_delete=models.PROTECT, null=True)
    task = models.ForeignKey(
        'WorkflowEngine.ProcessTask',
        on_delete=models.SET_NULL,
        null=True,
        related_name='structures',
    )
    related_structures = models.ManyToManyField(
        'self',
        through='tags.StructureRelation',
        through_fields=('structure_a', 'structure_b'),
        symmetrical=False,
    )

    def is_move_allowed(self, tag_structure, dst_tag_structure):
        current_version = tag_structure.tag.current_version
        rules = self.specification.get('rules', {}).get(current_version.type, {})

        if not rules.get('movable', True):
            return False

        return True

    def _create_template_instance(self):
        return Structure.objects.create(
            name=self.name,
            type=self.type,
            template=self,
            is_template=False,
            published=False,
            published_date=None,
            version=self.version,
            version_link=self.version_link,
            start_date=self.start_date,
            end_date=self.end_date,
            specification=self.specification,
            rule_convention_type=self.rule_convention_type,
        )

    def create_template_instance(self, archive_tag):
        new_structure = self._create_template_instance()

        archive_tagstructure = TagStructure.objects.create(tag=archive_tag, structure=new_structure)

        # create descendants from structure
        for unit in self.units.prefetch_related('notes', 'identifiers').select_related('parent'):
            unit.create_template_instance(new_structure)

        return new_structure, archive_tagstructure

    def _get_unit_by_ref_cache_key(self, reference_code):
        return '{}_ref_{}'.format(str(self.pk), reference_code)

    def get_unit_by_ref(self, reference_code):
        cache_key = self._get_unit_by_ref_cache_key(reference_code)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        unit = self.units.get(reference_code=reference_code)
        cache.set(cache_key, unit.pk, 60)
        return unit.pk

    def _create_new_version(self, version_name):
        return Structure.objects.create(
            name=self.name,
            type=self.type,
            template=self.template,
            is_template=self.is_template,
            published=False,
            published_date=None,
            version=version_name,
            version_link=self.version_link,
            start_date=self.start_date,
            end_date=self.end_date,
            specification=self.specification,
            rule_convention_type=self.rule_convention_type,
        )

    def create_new_version(self, version_name):
        new_structure = self._create_new_version(version_name)

        # create descendants from structure
        for unit in StructureUnit.objects.filter(structure=self):
            unit.create_new_version(new_structure)

        return new_structure

    def is_new_version(self):
        return Structure.objects.filter(
            is_template=True, published=True,
            version_link=self.version_link
        ).exclude(
            pk=self.pk
        ).exists()

    def get_last_version(self):
        return Structure.objects.filter(
            is_template=True, published=True,
            version_link=self.version_link,
        ).latest('published_date')

    def is_compatible_with_other_structure(self, other):
        for old_unit in other.units.iterator():
            assert old_unit.related_structure_units.filter(structure=self).exists()

        return True

    def is_compatible_with_last_version(self):
        last_version = self.get_last_version()
        return self.is_compatible_with_other_structure(last_version)

    def publish(self):
        from ESSArch_Core.tags.documents import StructureUnitDocument
        if self.is_new_version():
            # TODO: What if multiple users wants to create a new version in parallel?
            # Use permissions to stop it?

            self.is_compatible_with_last_version()
            last_version = self.get_last_version()

            for old_instance in last_version.instances.all():
                archive_tag_structure = old_instance.tagstructure_set.get(
                    structure_unit__isnull=True, parent__isnull=True
                )
                new_instance, new_archive_tag_structure = self.create_template_instance(archive_tag_structure.tag)
                for instance_unit in new_instance.units.all():
                    StructureUnitDocument.from_obj(instance_unit).save()

                archive_tag_structure.copy_descendants_to_new_structure(new_instance)

        self.is_editable = False
        self.published = True
        self.published_date = timezone.now()
        self.save()

    def unpublish(self):
        self.published = False
        self.save()

    @transaction.atomic
    def relate_to(self, other_structure, relation_type, **kwargs):
        StructureRelation.objects.create(
            structure_a=self,
            structure_b=other_structure,
            type=relation_type,
            **kwargs,
        )

        # create mirrored relation
        StructureRelation.objects.create(
            structure_a=other_structure,
            structure_b=self,
            type=relation_type.mirrored_type or relation_type,
            **kwargs,
        )

    def __str__(self):
        return '{} {}'.format(self.name, self.version)

    class Meta:
        get_latest_by = 'create_date'
        permissions = (
            ('publish_structure', 'Can publish structures'),
            ('unpublish_structure', 'Can unpublish structures'),
            ('create_new_structure_version', 'Can create new structure versions'),
        )


class StructureUnitType(models.Model):
    structure_type = models.ForeignKey('StructureType', on_delete=models.CASCADE, verbose_name=_('structure type'))
    name = models.CharField(_('name'), max_length=255, blank=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('structure unit type')
        verbose_name_plural = _('structure unit types')


class StructureUnitRelation(models.Model):
    structure_unit_a = models.ForeignKey(
        'tags.StructureUnit',
        on_delete=models.CASCADE,
        related_name='structure_unit_relations_a',
    )
    structure_unit_b = models.ForeignKey(
        'tags.StructureUnit',
        on_delete=models.CASCADE,
        related_name='structure_unit_relations_b',
    )
    type = models.ForeignKey('tags.NodeRelationType', on_delete=models.PROTECT, null=False)
    description = models.TextField(_('description'), blank=True)
    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)
    create_date = models.DateTimeField(_('create date'), default=timezone.now)
    revise_date = models.DateTimeField(_('revise date'), auto_now=True)

    class Meta:
        unique_together = ('structure_unit_a', 'structure_unit_b', 'type')  # Avoid duplicates within same type


class StructureUnitManager(TreeManager, OrganizationManager):
    pass


class StructureUnit(MPTTModel):
    structure = models.ForeignKey('tags.Structure', on_delete=models.CASCADE, null=False, related_name='units')
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, related_name='children', db_index=True)
    name = models.CharField(max_length=255)
    type = models.ForeignKey('tags.StructureUnitType', on_delete=models.PROTECT)
    template = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True,
        limit_choices_to={'structure__is_template': True}, related_name='instances', verbose_name=_('template'),
    )
    description = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    reference_code = models.CharField(max_length=255, db_index=True)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    transfers = models.ManyToManyField('tags.Transfer', verbose_name=_('transfers'), related_name='structure_units')
    task = models.ForeignKey(
        'WorkflowEngine.ProcessTask',
        on_delete=models.SET_NULL,
        null=True,
        related_name='structure_units',
    )
    related_structure_units = models.ManyToManyField(
        'self',
        through='tags.StructureUnitRelation',
        through_fields=('structure_unit_a', 'structure_unit_b'),
        symmetrical=False,
    )

    @transaction.atomic
    def copy_to_structure(self, structure, template_unit=None):
        old_parent_ref_code = getattr(self.parent, 'reference_code', None)
        parent = None

        if old_parent_ref_code is not None:
            parent = structure.get_unit_by_ref(old_parent_ref_code)

        new_unit = StructureUnit.objects.create(
            structure=structure,
            parent_id=parent,
            name=self.name,
            type=self.type,
            description=self.description,
            comment=self.comment,
            reference_code=self.reference_code,
            start_date=self.start_date,
            end_date=self.end_date,
            template=template_unit,
        )

        ref_cache_key = structure._get_unit_by_ref_cache_key(self.reference_code)
        cache.set(ref_cache_key, new_unit.pk, 60)

        for identifier in self.identifiers.all():
            NodeIdentifier.objects.create(
                structure_unit_id=new_unit.pk,
                identifier=identifier.identifier,
                type=identifier.type,
            )

        for note in self.notes.all():
            NodeNote.objects.create(
                structure_unit_id=new_unit.pk,
                text=note.text,
                type=note.type,
                href=note.href,
                create_date=note.create_date,
                revise_date=note.revise_date,
            )

        return new_unit

    def create_template_instance(self, structure_instance):
        new_unit = self.copy_to_structure(structure_instance, template_unit=self)

        new_archive_structure = new_unit.structure.tagstructure_set.first().get_root()
        for relation in StructureUnitRelation.objects.filter(structure_unit_a=self):
            if relation.structure_unit_b.structure.is_template:
                try:
                    related_unit_instance = StructureUnit.objects.get(
                        template=relation.structure_unit_b,
                        structure__tagstructure__tag=new_archive_structure.tag,
                    )
                except StructureUnit.DoesNotExist:
                    continue

                StructureUnitRelation.objects.create(
                    structure_unit_a=new_unit,
                    structure_unit_b=related_unit_instance,
                    type=relation.type,
                    description=relation.description,
                    start_date=relation.start_date,
                    end_date=relation.end_date,
                    create_date=relation.create_date,
                    revise_date=relation.revise_date,
                )

                continue

            related_archive_structure = relation.structure_unit_b.structure.tagstructure_set.first().get_root()

            if new_archive_structure.tag != related_archive_structure.tag:
                continue

            StructureUnitRelation.objects.create(
                structure_unit_a=new_unit,
                structure_unit_b=relation.structure_unit_b,
                type=relation.type,
                description=relation.description,
                start_date=relation.start_date,
                end_date=relation.end_date,
                create_date=relation.create_date,
                revise_date=relation.revise_date,
            )

        for relation in StructureUnitRelation.objects.filter(structure_unit_b=self):
            if relation.structure_unit_a.structure.is_template:
                try:
                    related_unit_instance = StructureUnit.objects.get(
                        template=relation.structure_unit_a,
                        structure__tagstructure__tag=new_archive_structure.tag,
                    )
                except StructureUnit.DoesNotExist:
                    continue

                StructureUnitRelation.objects.create(
                    structure_unit_a=related_unit_instance,
                    structure_unit_b=new_unit,
                    type=relation.type,
                    description=relation.description,
                    start_date=relation.start_date,
                    end_date=relation.end_date,
                    create_date=relation.create_date,
                    revise_date=relation.revise_date,
                )

                continue

            related_archive_structure = relation.structure_unit_a.structure.tagstructure_set.first().get_root()

            if new_archive_structure.tag != related_archive_structure.tag:
                continue

            StructureUnitRelation.objects.create(
                structure_unit_a=relation.structure_unit_a,
                structure_unit_b=new_unit,
                type=relation.type,
                description=relation.description,
                start_date=relation.start_date,
                end_date=relation.end_date,
                create_date=relation.create_date,
                revise_date=relation.revise_date,
            )

            # copy existing tag structures to new unit
            old_tag_structures = TagStructure.objects.filter(
                structure_unit=relation.structure_unit_a,
                tree_id=related_archive_structure.tree_id,
            )
            for old_tag_structure in old_tag_structures.get_descendants(include_self=True):
                if old_tag_structure.structure_unit is None:
                    old_tag_structure.copy_to_new_structure(new_unit.structure)
                    continue

                old_tag_structure.copy_to_new_structure(new_unit.structure, new_unit)

        return new_unit

    def create_new_version(self, new_structure):
        unit = self.copy_to_structure(new_structure)

        cache_key = 'version_node_relation_type'
        relation_type = cache.get(cache_key)

        if relation_type is None:
            relation_type, _ = NodeRelationType.objects.get_or_create(name='new version')
            cache.set(relation_type, relation_type, timeout=3600)

        StructureUnitRelation.objects.create(
            structure_unit_a=self,
            structure_unit_b=unit,
            type=relation_type,
        )

        return unit

    @transaction.atomic
    def relate_to(self, other_unit, relation_type, **kwargs):
        StructureUnitRelation.objects.create(
            structure_unit_a=self,
            structure_unit_b=other_unit,
            type=relation_type,
            **kwargs,
        )

        if self.structure != other_unit.structure:
            if not self.structure.is_template and not other_unit.structure.is_template:
                src_archive_structure = self.structure.tagstructure_set.first().get_root()
                dst_archive_structure = other_unit.structure.tagstructure_set.first().get_root()

                if src_archive_structure == dst_archive_structure:
                    # copy existing tag structures to other unit
                    old_tag_structures = TagStructure.objects.filter(structure_unit=self)
                    for old_tag_structure in old_tag_structures.get_descendants(include_self=True):
                        if old_tag_structure.structure_unit is None:
                            old_tag_structure.copy_to_new_structure(other_unit.structure)
                            continue

                        old_tag_structure.copy_to_new_structure(other_unit.structure, other_unit)

            if not self.structure.is_template and other_unit.structure.is_template:
                # copy tagstructures to instance in same archive of related template

                archive_structure = self.structure.tagstructure_set.first().get_root()
                try:
                    related_unit_instance = StructureUnit.objects.get(
                        structure__template=other_unit.structure,
                        structure__tagstructure__tag=archive_structure.tag,
                    )
                except StructureUnit.DoesNotExist:
                    pass
                else:
                    related_structure_instance = related_unit_instance.structure

                    # copy existing tag structures to other unit
                    old_tag_structures = TagStructure.objects.filter(structure_unit=self)
                    for old_tag_structure in old_tag_structures.get_descendants(include_self=True):
                        if old_tag_structure.structure_unit is None:
                            old_tag_structure.copy_to_new_structure(related_structure_instance)
                            continue

                        old_tag_structure.copy_to_new_structure(related_structure_instance, related_unit_instance)

        # create mirrored relation
        StructureUnitRelation.objects.create(
            structure_unit_a=other_unit,
            structure_unit_b=self,
            type=relation_type.mirrored_type or relation_type,
            **kwargs,
        )

    def get_related_in_other_structure(self, other_structure):
        structure = self.structure
        other_structure_template = other_structure if other_structure.is_template else other_structure.template

        template_unit = self if structure.is_template else self.template
        template_units = template_unit.related_structure_units.filter(structure=other_structure_template)

        if other_structure.is_template:
            return template_units

        return StructureUnit.objects.filter(template__in=template_units)

    def __str__(self):
        return '{} {}'.format(self.reference_code, self.name)

    objects = StructureUnitManager()

    class Meta:
        unique_together = (('structure', 'reference_code'),)
        permissions = (
            ('add_structureunit_instance', _('Can add structure unit instances')),
            ('change_structureunit_instance', _('Can change instances of structure units')),
            ('delete_structureunit_instance', _('Can delete instances of structure units')),
            ('move_structureunit_instance', _('Can move instances of structure units')),
        )


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    current_version = models.ForeignKey(
        'tags.TagVersion',
        on_delete=models.SET_NULL,
        null=True,
        related_name='current_version_tags'
    )
    information_package = models.ForeignKey(
        'ip.InformationPackage',
        on_delete=models.CASCADE,
        null=True,
        related_name='tags'
    )
    task = models.ForeignKey('WorkflowEngine.ProcessTask', on_delete=models.SET_NULL, null=True, related_name='tags')

    objects = OrganizationManager()

    def get_structures(self, structure=None):
        query_filter = {}
        structures = self.structures
        if structure is not None:
            query_filter['structure'] = structure
            structures = structures.filter(**query_filter)

        return structures

    def get_active_structure(self):
        return self.structures.latest()

    def get_root(self, structure=None):
        try:
            return self.get_structures(structure).latest().get_root().tag
        except TagStructure.DoesNotExist:
            return None

    def get_parent(self, structure=None):
        try:
            return self.get_structures(structure).latest().parent.tag
        except TagStructure.DoesNotExist:
            return None

    def get_children(self, structure=None):
        try:
            structure_children = self.get_structures(structure).latest().get_children()
            return Tag.objects.filter(structures__in=Subquery(structure_children.values('pk')))
        except TagStructure.DoesNotExist:
            return Tag.objects.none()

    def get_descendants(self, structure=None, include_self=False):
        try:
            structure_descendants = self.get_structures(structure).latest().get_descendants(include_self=include_self)
            return Tag.objects.filter(structures__in=structure_descendants)
        except TagStructure.DoesNotExist:
            return Tag.objects.none()

    def is_leaf_node(self, structure=None):
        try:
            return self.get_structures(structure).latest().is_leaf_node()
        except TagStructure.DoesNotExist:
            return True

    def __str__(self):
        try:
            return '{}'.format(self.current_version)
        except TagVersion.DoesNotExist:
            return '{}'.format(self.pk)

    class Meta:
        permissions = (
            ('search', 'Can search'),
            ('create_archive', 'Can create new archives'),
            ('change_archive', 'Can change archives'),
            ('delete_archive', 'Can delete archives'),
            ('change_tag_location', 'Can change tag location'),
        )


class TagVersionRelation(models.Model):
    tag_version_a = models.ForeignKey(
        'tags.TagVersion',
        on_delete=models.CASCADE,
        related_name='tag_version_relations_a',
    )
    tag_version_b = models.ForeignKey(
        'tags.TagVersion',
        on_delete=models.CASCADE,
        related_name='tag_version_relations_b',
    )
    type = models.ForeignKey('tags.NodeRelationType', on_delete=models.PROTECT, null=False)
    description = models.TextField(_('description'), blank=True)
    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)
    create_date = models.DateTimeField(_('create date'), default=timezone.now)
    revise_date = models.DateTimeField(_('revise date'), auto_now=True)

    class Meta:
        unique_together = ('tag_version_a', 'tag_version_b', 'type')  # Avoid duplicates within same type


class MediumType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False)
    size = models.CharField(_('size'), max_length=255, blank=False)
    unit = models.CharField(_('unit'), max_length=255, blank=False)

    class Meta:
        unique_together = ('name', 'size', 'unit')  # Avoid duplicates


class MetricType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('metric type')
        verbose_name_plural = _('metric types')


class LocationLevelType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('location level type')
        verbose_name_plural = _('location level types')


class LocationFunctionType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('location function type')
        verbose_name_plural = _('location function types')


class LocationManager(TreeManager, OrganizationManager):
    pass


class Location(MPTTModel):
    name = models.CharField(_('name'), max_length=255, blank=False)
    parent = TreeForeignKey(
        'self', on_delete=models.SET_NULL, null=True, related_name='children', verbose_name=_('parent')
    )
    metric = models.ForeignKey(MetricType, on_delete=models.PROTECT, null=True, verbose_name=_('metric'))
    capacity = models.IntegerField(_('capacity'), null=True)  # FloatField or DecimalField instead?
    level_type = models.ForeignKey(LocationLevelType, on_delete=models.PROTECT, verbose_name=_('level type'))
    function = models.ForeignKey(LocationFunctionType, on_delete=models.PROTECT, verbose_name=_('function'))

    objects = LocationManager()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('location')
        verbose_name_plural = _('locations')


class TagVersionType(models.Model):
    unique_information_package_type_error = _(
        'Only 1 node type can be set as information package type at a time'
    )
    information_package_type_not_found_error = _(
        'Node information package type not found'
    )

    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)
    archive_type = models.BooleanField(_('archive type'), default=False)
    custom_fields_template = JSONField(default=[], blank=True)
    information_package_type = models.BooleanField(_('information package type'), default=False)

    def clean(self):
        if self.information_package_type:
            try:
                existing = TagVersionType.objects.get(information_package_type=True)
                if existing != self:
                    raise ValidationError(
                        self.unique_information_package_type_error,
                        code='invalid',
                    )
            except TagVersionType.DoesNotExist:
                pass

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('node type')
        verbose_name_plural = _('node types')


class TagVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tag = models.ForeignKey('tags.Tag', on_delete=models.CASCADE, related_name='versions')
    reference_code = models.CharField(max_length=255, blank=True)
    type = models.ForeignKey('tags.TagVersionType', on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    elastic_index = models.CharField(max_length=255, blank=False, default=None)
    create_date = models.DateTimeField(default=timezone.now, null=True)
    revise_date = models.DateTimeField(auto_now=True)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    import_date = models.DateTimeField(null=True)
    medium_type = models.ForeignKey(
        'tags.MediumType',
        on_delete=models.PROTECT,
        related_name='tag_versions',
        null=True
    )
    metric = models.ForeignKey(MetricType, on_delete=models.PROTECT, null=True, verbose_name=_('metric'))
    capacity = models.IntegerField(_('capacity'), null=True)  # FloatField or DecimalField instead?
    location = models.ForeignKey(Location, on_delete=models.PROTECT, null=True, verbose_name=_('location'))
    transfers = models.ManyToManyField('tags.Transfer', verbose_name=_('transfers'), related_name='tag_versions')
    custom_fields = JSONField(default={})

    def to_search_doc(self):
        try:
            current_structure = self.tag.get_active_structure()
            parent = current_structure.parent
            if parent is not None:
                parent = {
                    'id': str(parent.tag.current_version.pk),
                    'index': parent.tag.current_version.elastic_index,
                }
        except TagStructure.DoesNotExist:
            parent = None

        data = {
            'reference_code': self.reference_code,
            'name': self.name,
            'type': self.type,
            'current_version': self.tag.current_version == self,
            'parent': parent,
        }

        if self.elastic_index != 'archive':
            archive = self.get_root()
            if archive is not None:
                data['doc'] = str(archive.pk)

        return data

    def to_search_data(self):
        return {
            '_id': self.pk,
            '_index': self.elastic_index,
            'current_version': self.tag.current_version == self,
            'reference_code': self.reference_code,
            'name': self.name,
            'type': self.type,
        }

    def to_search(self):  # TODO: replace with from_obj
        from ESSArch_Core.tags.documents import VersionedDocType

        d = self.to_search_data()
        return VersionedDocType(**d)

    def from_search(self):
        es = get_connection()
        return es.get(
            index=self.elastic_index,
            doc_type='_all',
            id=str(self.pk),
            params={'_source_exclude': 'attachment.content'}
        )

    def get_doc(self):
        from ESSArch_Core.search.documents import DocumentBase
        from ESSArch_Core.tags.documents import (
            Archive,
            Component,
            Directory,
            File,
        )

        cls = None
        kwargs = {'params': {}}

        if self.elastic_index == 'archive':
            cls = Archive
        elif self.elastic_index == 'component':
            cls = Component
        elif self.elastic_index == 'directory':
            cls = Directory
        elif self.elastic_index == 'document':
            kwargs['params']['_source_exclude'] = 'attachment.content'
            cls = File
        else:
            cls = DocumentBase

        return cls.get(index=self.elastic_index, id=str(self.pk), **kwargs)

    def update_search(self, data):
        doc = self.to_search_data()

        if 'parent' not in data:
            try:
                current_structure = self.tag.get_active_structure()
                parent = current_structure.parent
                if parent is not None:
                    parent = {
                        'id': str(parent.tag.current_version.pk),
                        'index': parent.tag.current_version.elastic_index,
                    }
            except TagStructure.DoesNotExist:
                parent = None

            data['parent'] = parent

        doc.update(data)
        doc['current_version'] = self.tag.current_version == self

        doc.pop('_id', None)
        doc.pop('_index', None)
        doc = {'doc_as_upsert': True, 'doc': doc}
        es = get_connection()
        es.update(self.elastic_index, 'doc', str(self.pk), body=doc)

    def create_new(self, start_date=None, end_date=None, data=None):
        # TODO: lock this version (e.g. using Redis) to make sure no one edits
        # the data in elastic while a new version is being created. If someone
        # queues a change to the old version after this version is created we
        # "lose" that change.

        if data is None:
            data = {}

        # create copies with same tag as old version
        new = TagVersion.objects.create(
            tag=self.tag,
            type=self.type,
            name=self.name,
            elastic_index=self.elastic_index,
            start_date=start_date,
            end_date=end_date
        )

        # TODO: create new copy of old elastic document updated with `data`
        doc = new.to_search()
        old_data = self.from_search()['_source']

        new_data = old_data
        new_data['current_version'] = False
        new_data.update(data)

        for (key, value) in new_data.items():
            setattr(doc, key, value)

        doc.save()

        return new

    def set_as_current_version(self):
        es = get_connection()
        Tag.objects.filter(pk=self.tag.pk).update(current_version=self)
        other_versions = [str(x) for x in
                          TagVersion.objects.filter(tag=self.tag).exclude(pk=self.pk).values_list('pk', flat=True)]

        # update other versions
        es.update_by_query(index=self.elastic_index,
                           body={"script": {"source": "ctx._source.current_version=false", "lang": "painless"},
                                 "query": {"terms": {"_id": other_versions}}})

        # update this version
        es.update_by_query(index=self.elastic_index,
                           body={"script": {"source": "ctx._source.current_version=true", "lang": "painless"},
                                 "query": {"term": {"_id": str(self.pk)}}})

    def get_structures(self, structure=None):
        query_filter = {}
        structures = self.tag.structures
        if structure is not None:
            query_filter['structure'] = structure
            structures = structures.filter(**query_filter)

        return structures

    def get_active_structure(self):
        return self.tag.get_active_structure()

    def get_root(self, structure=None):
        try:
            return self.tag.get_root(structure).current_version
        except AttributeError:
            return None

    def get_parent(self, structure=None):
        try:
            return self.tag.get_parent(structure).current_version
        except AttributeError:
            return None

    def get_children(self, structure=None):
        tag_children = self.tag.get_children(structure)
        return TagVersion.objects.filter(
            tag__current_version=F('pk'), tag__in=Subquery(tag_children.values('pk'))
        ).select_related('tag')

    def get_descendants(self, structure=None, include_self=False):
        tag_descendants = self.tag.get_descendants(structure, include_self=include_self)
        return TagVersion.objects.filter(tag__current_version=F('pk'), tag__in=tag_descendants).select_related('tag')

    def is_leaf_node(self, structure=None):
        return self.tag.is_leaf_node(structure)

    def __str__(self):
        return '{} {}'.format(self.reference_code, self.name)

    objects = OrganizationManager()

    class Meta:
        get_latest_by = 'create_date'
        ordering = ('reference_code',)


class TagStructure(MPTTModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tag = models.ForeignKey('tags.Tag', on_delete=models.CASCADE, related_name='structures')
    structure = models.ForeignKey(
        'tags.Structure', on_delete=models.PROTECT, null=False,
        limit_choices_to={'is_template': False}
    )
    structure_unit = models.ForeignKey(
        'tags.StructureUnit', on_delete=models.PROTECT, null=True,
        limit_choices_to={'structure__is_template': False}
    )
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, related_name='children', db_index=True)
    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)

    def copy_to_new_structure(self, new_structure, new_unit=None):
        new_parent_tag = None

        if self.parent is not None:
            try:
                old_parent_tag = self.parent.tag
                new_parent_tag = old_parent_tag.structures.get(structure=new_structure)
            except TagStructure.DoesNotExist:
                logger.exception('Parent tag of {self} does not exist in new structure {new_structure}')
                raise

        if new_unit is None and self.structure_unit is not None:
            try:
                new_unit = self.structure_unit.get_related_in_other_structure(new_structure).get()
            except StructureUnit.DoesNotExist:
                logger.exception('Structure unit instance of {self} does not exist in new structure {new_structure}')
                raise

        return TagStructure.objects.create(
            tag_id=self.tag_id, structure=new_structure,
            structure_unit=new_unit, parent=new_parent_tag,
        )

    @transaction.atomic
    def copy_descendants_to_new_structure(self, new_structure):
        for old_descendant in self.get_descendants(include_self=False):
            old_descendant.copy_to_new_structure(new_structure)

    def create_new(self, representation):
        tree_id = self.__class__.objects._get_next_tree_id()
        new_objs = []

        def create_copy(tag, representation):
            # create copies with same parent as old version
            return TagStructure(tag_id=tag.tag_id, structure=representation, parent_id=tag.parent_id,
                                tree_id=tree_id, lft=0, rght=0, level=0,)

        with transaction.atomic():
            with TagStructure.objects.disable_mptt_updates():
                new_self = create_copy(self, representation)
                new_self.save()

                for tag in self.get_descendants(include_self=False):
                    new = create_copy(tag, representation)
                    new_objs.append(new)

                TagStructure.objects.bulk_create(new_objs, batch_size=100)

                # set parent to latest representation of all nodes except self

                latest_parent = TagStructure.objects.filter(
                    tag=OuterRef('parent_tag'),
                    structure=OuterRef('structure'))

                new_tags = TagStructure.objects.filter(structure_id=representation.pk) \
                    .exclude(tag=self.tag) \
                    .annotate(parent_tag=F('parent__tag_id')) \
                    .annotate(latest_parent=Subquery(latest_parent.values('pk')[:1]))

                for new_tag in new_tags:
                    new_tag.parent_id = new_tag.latest_parent
                    new_tag.save(update_fields=['parent_id'])

            TagStructure.objects.partial_rebuild(new_self.tree_id)

        return new_self

    def __str__(self):
        return '{} in {}'.format(self.tag, self.structure)

    class Meta:
        get_latest_by = 'structure__create_date'
        ordering = ('structure__create_date',)


class Search(models.Model):
    query = JSONField(null=False)
    name = models.CharField(max_length=255, blank=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='searches')


class DeliveryType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('delivery type')
        verbose_name_plural = _('delivery types')


class Delivery(models.Model):
    id = models.BigAutoField(primary_key=True)
    reference_code = models.CharField(_('name'), max_length=255, blank=True)
    name = models.CharField(_('name'), max_length=255, blank=False)
    type = models.ForeignKey('tags.DeliveryType', on_delete=models.PROTECT, null=False, verbose_name=_('type'))
    description = models.TextField(_('description'), blank=True)

    producer_organization = models.ForeignKey(
        Agent,
        on_delete=models.PROTECT,
        related_name='deliveries',
        default=None,
        null=True,
    )

    submission_agreement = models.ForeignKey(
        SubmissionAgreement,
        on_delete=models.PROTECT,
        related_name='deliveries',
        default=None,
        null=True,
    )

    objects = OrganizationManager()

    class Meta:
        verbose_name = _('delivery')
        verbose_name_plural = _('deliveries')


class Transfer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('name'), max_length=255, blank=False)
    delivery = models.ForeignKey('tags.Delivery', on_delete=models.CASCADE, null=False, verbose_name=_('delivery'))
    submitter_organization = models.CharField(blank=True, max_length=255)
    submitter_organization_main_address = models.CharField(blank=True, max_length=255)
    submitter_individual_name = models.CharField(blank=True, max_length=255)
    submitter_individual_phone = models.CharField(blank=True, max_length=255)
    submitter_individual_email = models.CharField(blank=True, max_length=255)
    description = models.TextField(blank=True)

    objects = OrganizationManager()

    class Meta:
        verbose_name = _('transfer')
        verbose_name_plural = _('transfers')
