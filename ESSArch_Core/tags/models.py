import uuid

import jsonfield
from django.db import models, transaction
from django.db.models import F, OuterRef, Subquery
from django.utils.translation import ugettext_lazy as _
from elasticsearch_dsl.connections import get_connection
from countries_plus.models import Country
from languages_plus.models import Language
from mptt.models import MPTTModel, TreeForeignKey

from ESSArch_Core.tags.documents import VersionedDocType


class AgentRelationType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)


class AgentRelation(models.Model):
    agent_a = models.ForeignKey('tags.Agent', on_delete=models.CASCADE, related_name='agent_relations_a')
    agent_b = models.ForeignKey('tags.Agent', on_delete=models.CASCADE, related_name='agent_relations_b')
    type = models.ForeignKey('tags.AgentRelationType', on_delete=models.PROTECT, null=False)
    description = models.TextField(_('description'), blank=True)
    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)
    create_date = models.DateTimeField(_('create date'), auto_now_add=True)
    revise_date = models.DateTimeField(_('revise date'), auto_now=True)

    class Meta():
        unique_together = ('agent_a', 'agent_b', 'type')  # Avoid duplicates within same type


class Agent(models.Model):
    MINIMAL = 0
    PARTIAL = 1
    FULL = 2
    LEVEL_OF_DETAIL_CHOICES = (
        (MINIMAL, _('minimal')),
        (PARTIAL, _('partial')),
        (FULL, _('full')),
    )

    DRAFT = 0
    FINAL = 1
    RECORD_STATUS_CHOICES = (
        (DRAFT, _('draft')),
        (FINAL, _('final')),
    )

    LATIN = 0
    SCRIPT_CHOICES = (
        (LATIN, _('latin')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    places = models.ManyToManyField('tags.Topography', through='tags.AgentPlace', related_name='agents')
    type = models.ForeignKey('tags.AgentType', on_delete=models.PROTECT, null=False, related_name='agents')
    ref_code = models.ForeignKey('tags.RefCode', on_delete=models.PROTECT, null=False, related_name='agents')
    related_agents = models.ManyToManyField(
        'self',
        through='tags.AgentRelation',
        through_fields=('agent_a', 'agent_b'),
        symmetrical=False,
    )
    level_of_detail = models.IntegerField(_('level of detail'), choices=LEVEL_OF_DETAIL_CHOICES, null=False)
    record_status = models.IntegerField(_('record status'), choices=RECORD_STATUS_CHOICES, null=False)
    script = models.IntegerField(_('record status'), choices=RECORD_STATUS_CHOICES, null=False)

    language = models.ForeignKey(Language, on_delete=models.PROTECT, null=False, verbose_name=_('language'))
    mandates = models.ManyToManyField('tags.SourcesOfAuthority', related_name='agents', verbose_name=_('mandates'))

    create_date = models.DateTimeField(_('create date'), null=False)
    revise_date = models.DateTimeField(_('revise date'), null=True)

    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)

    tags = models.ManyToManyField('tags.TagVersion', through='tags.AgentTagLink', related_name='agents')
    task = models.ForeignKey('WorkflowEngine.ProcessTask', on_delete=models.SET_NULL, null=True, related_name='agents')


class AgentTagLink(models.Model):
    agent = models.ForeignKey(
        'tags.Agent',
        on_delete=models.CASCADE,
        null=False,
        related_name='tag_links',
        verbose_name=_('agent')
    )
    tag = models.ForeignKey(
        'tags.TagVersion',
        on_delete=models.CASCADE,
        null=False,
        related_name='agent_links',
        verbose_name=_('tag')
    )
    type = models.ForeignKey(
        'tags.AgentTagLinkRelationType',
        on_delete=models.PROTECT,
        null=False,
        verbose_name=_('type')
    )
    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)
    description = models.TextField(_('description'), blank=True)


class AgentTagLinkRelationType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)


class AgentNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        'tags.Agent',
        on_delete=models.CASCADE,
        null=False,
        related_name='notes',
        verbose_name=_('agent')
    )
    type = models.ForeignKey('tags.AgentNoteType', on_delete=models.PROTECT, null=False, verbose_name=_('type'))
    text = models.TextField(_('text'), blank=False)
    create_date = models.DateTimeField(_('create date'), null=False)
    revise_date = models.DateTimeField(_('revise date'), null=True)


class AgentNoteType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)


class AgentFunction(models.Model):
    """
    TODO:
        1. figure out which fields to add
        2. add them
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey('tags.Agent', on_delete=models.CASCADE, null=False, related_name='functions')


class SourcesOfAuthority(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.ForeignKey('tags.AuthorityType', on_delete=models.PROTECT, null=False)
    name = models.TextField(_('name'), blank=False)
    description = models.TextField(_('description'), blank=True)
    href = models.TextField(_('href'), blank=True)
    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)


class AuthorityType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)


class AgentIdentifier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identifier = models.TextField(_('identifier'), blank=False)
    agent = models.ForeignKey('tags.Agent', on_delete=models.CASCADE, null=False, related_name='identifiers')
    type = models.ForeignKey('tags.AgentIdentifierType', on_delete=models.PROTECT, null=False, verbose_name=_('type'))


class AgentIdentifierType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)


class Topography(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('name'), max_length=255)
    alt_name = models.TextField(_('alternative name'), blank=True)
    type = models.CharField(_('type'), max_length=255)
    main_category = models.TextField(_('main category'), blank=True)
    sub_category = models.TextField(_('sub category'), blank=True)
    reference_code = models.TextField(_('reference code'))
    start_year = models.DateField(_('start year'), null=True)
    end_year = models.DateField(_('end year'), null=True)
    lng = models.DecimalField(_('longitude'), max_digits=9, decimal_places=6, null=True)
    lat = models.DecimalField(_('latitude'), max_digits=9, decimal_places=6, null=True)

    class Meta():
        unique_together = ('name', 'type')  # Avoid duplicates within same type


class AgentPlaceType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)


class AgentPlace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey('tags.Agent', on_delete=models.CASCADE, null=False)
    topography = models.ForeignKey('tags.Topography', on_delete=models.CASCADE, null=True)
    type = models.ForeignKey('tags.AgentPlaceType', on_delete=models.PROTECT, null=False)
    description = models.TextField(_('description'), blank=True)
    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)


class AgentType(models.Model):
    CORPORATE_BODY = 'corporatebody'
    PERSON = 'person'
    FAMILY = 'family'
    CPF_CHOICES = (
        (CORPORATE_BODY, _('corporate body')),
        (PERSON, _('person')),
        (FAMILY, _('family')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cpf = models.CharField(max_length=20, choices=CPF_CHOICES, blank=False)
    main_type = models.ForeignKey('tags.MainAgentType', on_delete=models.PROTECT, null=False)
    sub_type = models.TextField(_('sub type'), blank=True)
    legal_status = models.TextField(_('legal status'), blank=False)


class MainAgentType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)


class AgentName(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey('tags.Agent', on_delete=models.CASCADE, null=False, related_name='names')
    main = models.TextField(_('main'), blank=False)
    part = models.TextField(_('part'), blank=True)
    description = models.TextField(_('description'), blank=True)
    type = models.ForeignKey('tags.AgentNameType', on_delete=models.PROTECT, null=False)
    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)
    certainty = models.NullBooleanField(_('certainty'))


class AgentNameType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)


class RefCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        null=False,
        related_name='ref_codes',
        verbose_name=_('country code')
    )
    repository_code = models.CharField(_('repository code'), max_length=255, blank=False)

    class Meta():
        unique_together = ('country', 'repository_code')


class Structure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=False)
    version = models.CharField(max_length=255, blank=False, default='1.0')
    version_link = models.UUIDField(default=uuid.uuid4, null=False)
    create_date = models.DateTimeField(auto_now_add=True)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    specification = jsonfield.JSONField(default={})
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


class StructureUnit(MPTTModel):
    structure = models.ForeignKey('tags.Structure', on_delete=models.CASCADE, null=False, related_name='units')
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, related_name='children', db_index=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
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
        return '{}'.format(self.current_version)

    class Meta:
        permissions = (
            ('search', 'Can search'),
            ('create_archive', 'Can create new archives'),
            ('delete_archive', 'Can delete archives'),
        )


class TagVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tag = models.ForeignKey('tags.Tag', on_delete=models.CASCADE, related_name='versions')
    reference_code = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    elastic_index = models.CharField(max_length=255, blank=False, default=None)
    create_date = models.DateTimeField(auto_now_add=True)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)

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

    def to_search(self):
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
