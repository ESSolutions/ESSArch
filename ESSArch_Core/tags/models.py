import uuid

import jsonfield
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models import F, OuterRef, Subquery
from django.utils.translation import ugettext_lazy as _
from elasticsearch_dsl.connections import get_connection
from mptt.models import MPTTModel, TreeForeignKey


User = get_user_model()


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
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name


class NodeRelationType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name


class StructureType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name


class RuleConventionType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name


class Structure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=False)
    type = models.ForeignKey(StructureType, on_delete=models.PROTECT)
    version = models.CharField(max_length=255, blank=False, default='1.0')
    version_link = models.UUIDField(default=uuid.uuid4, null=False)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name='created_structures')
    revised_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name='revised_structures')
    create_date = models.DateTimeField(auto_now_add=True)
    revise_date = models.DateTimeField(auto_now=True)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    specification = jsonfield.JSONField(default={})
    rule_convention_type = models.ForeignKey('tags.RuleConventionType', on_delete=models.PROTECT, null=True)
    task = models.ForeignKey(
        'WorkflowEngine.ProcessTask',
        on_delete=models.SET_NULL,
        null=True,
        related_name='structures',
    )

    def is_move_allowed(self, tag_structure, dst_tag_structure):
        current_version = tag_structure.tag.current_version
        rules = self.specification.get('rules', {}).get(current_version.type, {})

        if not rules.get('movable', True):
            return False

        return True

    def __str__(self):
        return '{} {}'.format(self.name, self.version)

    class Meta:
        get_latest_by = 'create_date'


class StructureUnitType(models.Model):
    structure_type = models.ForeignKey('StructureType', on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=False)

    def __str__(self):
        return self.name


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
    create_date = models.DateTimeField(_('create date'), auto_now_add=True)
    revise_date = models.DateTimeField(_('revise date'), auto_now=True)

    class Meta:
        unique_together = ('structure_unit_a', 'structure_unit_b', 'type')  # Avoid duplicates within same type


class StructureUnit(MPTTModel):
    structure = models.ForeignKey('tags.Structure', on_delete=models.CASCADE, null=False, related_name='units')
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, related_name='children', db_index=True)
    name = models.CharField(max_length=255)
    type = models.ForeignKey('tags.StructureUnitType', on_delete=models.PROTECT)
    description = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    reference_code = models.CharField(max_length=255)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
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

    def __str__(self):
        return '{} {}'.format(self.reference_code, self.name)

    class Meta:
        unique_together = (('structure', 'reference_code'),)


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
            return Tag.objects.filter(structures__in=structure_children)
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
            ('delete_archive', 'Can delete archives'),
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
    create_date = models.DateTimeField(_('create date'), auto_now_add=True)
    revise_date = models.DateTimeField(_('revise date'), auto_now=True)

    class Meta:
        unique_together = ('tag_version_a', 'tag_version_b', 'type')  # Avoid duplicates within same type


class MediumType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False)
    size = models.CharField(_('size'), max_length=255, blank=False)
    unit = models.CharField(_('unit'), max_length=255, blank=False)

    class Meta:
        unique_together = ('name', 'size', 'unit')  # Avoid duplicates


class TagVersionType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)
    archive_type = models.BooleanField(_('archive type'))

    def __str__(self):
        return self.name


class TagVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tag = models.ForeignKey('tags.Tag', on_delete=models.CASCADE, related_name='versions')
    reference_code = models.CharField(max_length=255, blank=True)
    type = models.ForeignKey('tags.TagVersionType', on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    elastic_index = models.CharField(max_length=255, blank=False, default=None)
    create_date = models.DateTimeField(auto_now_add=True)
    revise_date = models.DateTimeField(auto_now=True)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    medium_type = models.ForeignKey(
        'tags.MediumType',
        on_delete=models.PROTECT,
        related_name='tag_versions',
        null=True
    )

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

    def get_doc(self):  # TODO: do we need this?
        from ESSArch_Core.tags.documents import VersionedDocType

        kwargs = {'params': {}}
        if self.elastic_index == 'document':
            kwargs['params']['_source_exclude'] = 'attachment.content'

        return VersionedDocType.get(index=self.elastic_index, id=str(self.pk), **kwargs)

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
        return TagVersion.objects.filter(tag__current_version=F('pk'), tag__in=tag_children).select_related('tag')

    def get_descendants(self, structure=None, include_self=False):
        tag_descendants = self.tag.get_descendants(structure, include_self=include_self)
        return TagVersion.objects.filter(tag__current_version=F('pk'), tag__in=tag_descendants).select_related('tag')

    def is_leaf_node(self, structure=None):
        return self.tag.is_leaf_node(structure)

    def __str__(self):
        return '{} {}'.format(self.reference_code, self.name)

    class Meta:
        get_latest_by = 'create_date'
        ordering = ('reference_code',)


class TagStructure(MPTTModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tag = models.ForeignKey('tags.Tag', on_delete=models.CASCADE, related_name='structures')
    structure = models.ForeignKey('tags.Structure', on_delete=models.CASCADE, null=False)
    structure_unit = models.ForeignKey('tags.StructureUnit', on_delete=models.CASCADE, null=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, related_name='children', db_index=True)
    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)

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
    query = jsonfield.JSONField(null=False)
    name = models.CharField(max_length=255, blank=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='searches')
