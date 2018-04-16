import uuid

import six
from django.db import models, transaction
from django.db.models import F, OuterRef, Subquery
from elasticsearch import Elasticsearch
from mptt.models import MPTTModel, TreeForeignKey

from ESSArch_Core.tags.documents import VersionedDocType

es = Elasticsearch()


class Structure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=False)
    version = models.CharField(max_length=255, blank=False)
    version_link = models.UUIDField(default=uuid.uuid4, null=False)
    create_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        get_latest_by = 'create_date'


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    current_version = models.ForeignKey('tags.TagVersion', on_delete=models.SET_NULL, null=True, related_name='current_version_tags')

    def get_structures(self, structure=None):
        query_filter = {}
        structures = self.structures
        if structure is not None:
            query_filter['structure'] = structure
            structures = structures.filter(**query_filter)

        return structures

    def get_active_structure(self):
        return self.structures.latest()

    def get_parent(self, structure=None):
        return self.get_structures(structure).latest().parent

    def get_children(self, structure=None):
        structure_children = self.get_structures(structure).latest().get_children()
        return Tag.objects.filter(structures__in=structure_children)

    def get_descendants(self, structure=None):
        structure_descendants = self.get_structures(structure).latest().get_descendants(include_self=False)
        return Tag.objects.filter(structures__in=structure_descendants)

    def is_leaf_node(self, structure=None):
        return self.get_structures(structure).latest().is_leaf_node()

    class Meta:
        permissions = (
            ('search', 'Can search'),
        )


class TagVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tag = models.ForeignKey('tags.Tag', on_delete=models.CASCADE, related_name='versions')
    type = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    elastic_index = models.CharField(max_length=255, blank=False, default=None)
    create_date = models.DateTimeField(auto_now_add=True)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)

    def to_search(self):
        d = {
            '_id': self.pk,
            '_index': self.elastic_index,
            'current_version': self.tag.current_version==self,
            'name': self.name,
            'type': self.type,
        }

        return VersionedDocType(**d)

    def from_search(self):
        return es.get(index=self.elastic_index, doc_type='_all', id=str(self.pk))

    def update_search(self, data):
        doc = self.to_search()
        doc.update(**data)

    def create_new(self, start_date=None, end_date=None, data=None):
        # TODO: lock this version (e.g. using Redis) to make sure no one edits
        # the data in elastic while a new version is being created. If someone
        # queues a change to the old version after this version is created we
        # "lose" that change.

        if data is None:
            data = {}

        # create copies with same tag as old version
        new = TagVersion.objects.create(tag=self.tag, type=self.type, name=self.name, elastic_index=self.elastic_index, start_date=start_date, end_date=end_date)

        # TODO: create new copy of old elastic document updated with `data`
        doc = new.to_search()
        old_data = self.from_search()['_source']

        new_data = old_data
        new_data['current_version'] = False
        new_data.update(data)

        for (key, value) in six.iteritems(new_data):
            setattr(doc, key, value)

        doc.save()

        return new

    def set_as_current_version(self):
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
        return self.tag.structures.latest()

    def get_parent(self, structure=None):
        return self.get_structures(structure).latest().parent

    def get_children(self, structure=None):
        structure_children = self.get_structures(structure).latest().get_children()
        return TagVersion.objects.filter(tag__current_version=F('pk'), tag__structures__in=structure_children).select_related('tag')

    def get_descendants(self, structure=None):
        structure_descendants = self.get_structures(structure).latest().get_descendants(include_self=False)
        return TagVersion.objects.filter(tag__current_version=F('pk'), tag__structures__in=structure_descendants).select_related('tag')

    def is_leaf_node(self, structure=None):
        return self.get_structures(structure).latest().is_leaf_node()

    class Meta:
        get_latest_by = 'create_date'


class TagStructure(MPTTModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tag = models.ForeignKey('tags.Tag', on_delete=models.CASCADE, related_name='structures')
    structure = models.ForeignKey('tags.Structure', on_delete=models.PROTECT, null=False)
    parent = TreeForeignKey('self', null=True, related_name='children', db_index=True)

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

                TagStructure.objects.bulk_create(new_objs, batch_size=1000)

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

    class Meta:
        get_latest_by = 'structure__create_date'
        ordering = ('structure__create_date',)
