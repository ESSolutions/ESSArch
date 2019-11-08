from django.utils import timezone
from elasticsearch_dsl import (
    Boolean,
    Date,
    InnerDoc,
    Integer,
    Keyword,
    Long,
    MetaField,
    Nested,
    Object,
    Q,
    Text,
    analyzer,
    token_filter,
    tokenizer,
)

from ESSArch_Core.search.documents import DocumentBase
from ESSArch_Core.tags.models import StructureUnit, TagVersion

ngram_tokenizer = tokenizer('custom_ngram_tokenizer', type='ngram', min_gram=3,
                            max_gram=3)
ngram_analyzer = analyzer('custom_ngram_analyzer', tokenizer=ngram_tokenizer,
                          filter=['lowercase'])

autocomplete_filter = token_filter('autocomplete_filter', type='edge_ngram', min_gram=1, max_gram=20)
autocomplete_analyzer = analyzer(
    'autocomplete_analyzer',
    filter=[autocomplete_filter, 'lowercase'],
    tokenizer='standard'
)


class Node(InnerDoc):
    id = Keyword()
    index = Keyword()


class Restriction(InnerDoc):
    name = Keyword()
    fields = Keyword()
    permissions = Keyword()


class VersionedDocType(DocumentBase):
    name = Text(
        analyzer=autocomplete_analyzer,
        search_analyzer='standard',
        fields={'keyword': {'type': 'keyword'}}
    )  # unittitle
    reference_code = Text(
        analyzer=autocomplete_analyzer,
        search_analyzer='standard',
        fields={'keyword': {'type': 'keyword'}}
    )
    link_id = Keyword()
    current_version = Boolean()
    index_date = Date()
    personal_identification_numbers = Keyword()
    restrictions = Nested(Restriction)
    ip = Keyword()
    agents = Keyword()
    task_id = Keyword()

    def create_new_version(self, start_date=None, end_date=None, refresh=False):
        data = self.to_dict(include_meta=False)
        data['_index'] = self._index._name
        data['start_date'] = start_date
        data['end_date'] = end_date

        if data['start_date'] is not None and data['start_date'] <= timezone.now():
            self.update(current_version=False)
            data['current_version'] = True
        else:
            data['current_version'] = False

        new_obj = self.__class__(**data)
        new_obj.save(pipeline='add_timestamp', refresh=refresh)
        return new_obj

    def set_as_current_version(self):
        index = self._index._name
        versions = self.__class__.search(index=index).source(False).query(
            'bool', must=[Q('term', link_id=self.link_id)], must_not=[Q('term', _id=self._id)]
        ).execute()

        for version in versions:
            version.update(current_version=False)

        self.update(current_version=True)

    def get_masked_fields(self, user):
        fields = set()
        for restriction in self.restrictions:
            if not len(restriction.fields):
                continue

            for perm in restriction.permissions:
                if user is None or not user.has_perm(perm):
                    fields |= set(restriction.fields)

        return list(fields)


class InnerArchiveDocument(InnerDoc):
    id = Keyword()
    name = Text(
        analyzer=autocomplete_analyzer,
        search_analyzer='standard',
        fields={'keyword': {'type': 'keyword'}}
    )
    reference_code = Keyword()

    @classmethod
    def from_obj(cls, obj):
        doc = InnerArchiveDocument(
            id=str(obj.pk),
            name=obj.name,
            reference_code=obj.reference_code,
        )
        return doc


class StructureTypeDocument(InnerDoc):
    id = Keyword()
    name = Keyword()

    @classmethod
    def from_obj(cls, obj):
        doc = StructureTypeDocument(
            id=str(obj.pk),
            name=obj.name,
        )
        return doc


class InnerStructureDocument(InnerDoc):
    id = Keyword()
    name = Keyword()
    structure_type = Object(StructureTypeDocument)

    @classmethod
    def from_obj(cls, obj):
        doc = InnerStructureDocument(
            id=str(obj.pk),
            name=obj.name,
            type=StructureTypeDocument.from_obj(obj.type),
        )
        return doc


class ComponentStructureUnitDocument(InnerDoc):
    id = Keyword()
    name = Keyword()
    reference_code = Keyword()
    structure = Object(InnerStructureDocument)

    @classmethod
    def from_obj(cls, obj):
        doc = ComponentStructureUnitDocument(
            id=str(obj.pk),
            name=obj.name,
            reference_code=obj.reference_code,
            structure=InnerStructureDocument.from_obj(obj.structure),
        )
        return doc


class Component(VersionedDocType):
    unit_ids = Nested()  # unitid
    unit_dates = Nested()  # unitdate
    arrival_date = Date()
    decision_date = Date()
    preparation_date = Date()
    create_date = Date()
    dispatch_date = Date()
    last_usage_date = Date()
    desc = Text(analyzer=autocomplete_analyzer, search_analyzer='standard')
    type = Keyword()  # series, volume, etc.
    parent = Object(Node)
    archive = Nested(InnerArchiveDocument)
    structure_units = Nested(ComponentStructureUnitDocument)
    institution = Keyword()
    organization = Keyword()

    @classmethod
    def get_model(cls):
        return TagVersion

    @classmethod
    def get_index_queryset(cls):
        return TagVersion.objects.select_related('tag', 'type').filter(elastic_index='component')

    @classmethod
    def from_obj(cls, obj, archive=None):
        units = StructureUnit.objects.filter(tagstructure__tag__versions=obj)

        if archive is not None:
            archive_doc = InnerArchiveDocument.from_obj(archive)
        elif obj.get_root() is not None:
            archive_doc = InnerArchiveDocument.from_obj(obj.get_root())
        else:
            archive_doc = None

        if obj.tag.task is None:
            task_id = None
        else:
            task_id = str(obj.tag.task.pk)

        doc = Component(
            _id=str(obj.pk),
            id=str(obj.pk),
            task_id=task_id,
            archive=archive_doc,
            structure_units=[ComponentStructureUnitDocument.from_obj(unit) for unit in units],
            current_version=obj.tag.current_version == obj,
            name=obj.name,
            desc=obj.description,
            reference_code=obj.reference_code,
            type=obj.type.name,
            agents=[str(pk) for pk in obj.agents.values_list('pk', flat=True)],
            **obj.custom_fields,
        )
        return doc

    class Index:
        name = 'component'
        analyzers = [autocomplete_analyzer]

    class Meta:
        date_detection = MetaField('false')


class Archive(VersionedDocType):
    unit_ids = Nested()  # unitid
    unit_dates = Nested()  # unitdate
    desc = Text(analyzer=autocomplete_analyzer, search_analyzer='standard')
    type = Keyword()
    archive_creator = Keyword()
    archive_responsible = Keyword()
    institution = Keyword()
    organization = Keyword()
    organization_group = Integer()

    @classmethod
    def get_model(cls):
        return TagVersion

    @classmethod
    def get_index_queryset(cls):
        return TagVersion.objects.select_related('tag', 'type').filter(elastic_index='archive')

    @classmethod
    def from_obj(cls, obj):
        if obj.tag.task is None:
            task_id = None
        else:
            task_id = str(obj.tag.task.pk)

        doc = Archive(
            _id=str(obj.pk),
            id=str(obj.pk),
            task_id=task_id,
            current_version=obj.tag.current_version == obj,
            name=obj.name,
            type=obj.type.name,
            reference_code=obj.reference_code,
            agents=[str(pk) for pk in obj.agents.values_list('pk', flat=True)],
            **obj.custom_fields,
        )
        return doc

    class Index:
        name = 'archive'
        analyzers = [autocomplete_analyzer]

    class Meta:
        date_detection = MetaField('false')


class InformationPackageDocument(VersionedDocType):
    id = Keyword()  # @id
    object_identifier_value = Text(
        analyzer=ngram_analyzer,
        search_analyzer='standard',
        fields={'keyword': {'type': 'keyword'}}
    )
    start_date = Date()
    end_date = Date()
    institution = Keyword()
    organization = Keyword()

    @classmethod
    def get_model(cls):
        from ESSArch_Core.ip.models import InformationPackage
        return InformationPackage

    @classmethod
    def from_obj(cls, obj):
        doc = InformationPackageDocument(
            _id=str(obj.pk),
            id=str(obj.pk),
            object_identifier_value=obj.object_identifier_value,
            start_date=obj.start_date,
            end_date=obj.end_date,
        )
        return doc

    class Index:
        name = 'information_package'
        analyzers = [autocomplete_analyzer, ngram_analyzer]

    class Meta:
        date_detection = MetaField('false')


class File(Component):
    filename = Keyword()
    extension = Keyword()
    href = Keyword()  # @href
    size = Long()
    modified = Date()
    attachment = Object(
        properties={
            'date': Date()
        })

    class Index:
        name = 'document'
        analyzers = [autocomplete_analyzer]

    @classmethod
    def get_index_queryset(cls):
        return TagVersion.objects.select_related(
            'tag', 'tag__information_package', 'type',
        ).filter(elastic_index='document')

    @classmethod
    def from_obj(cls, obj, archive=None):
        units = StructureUnit.objects.filter(tagstructure__tag__versions=obj)

        if archive is not None:
            archive_doc = InnerArchiveDocument.from_obj(archive)
        elif obj.get_root() is not None:
            archive_doc = InnerArchiveDocument.from_obj(obj.get_root())
        else:
            archive_doc = None

        if obj.tag.task is None:
            task_id = None
        else:
            task_id = str(obj.tag.task.pk)
        ip_id = getattr(obj.tag.information_package, 'pk', None)
        ip_id = str(ip_id) if ip_id is not None else None

        doc = File(
            _id=str(obj.pk),
            id=str(obj.pk),
            task_id=task_id,
            archive=archive_doc,
            structure_units=[ComponentStructureUnitDocument.from_obj(unit) for unit in units],
            current_version=obj.tag.current_version == obj,
            name=obj.name,
            desc=obj.description,
            reference_code=obj.reference_code,
            type=obj.type.name,
            ip=ip_id,
            agents=[str(pk) for pk in obj.agents.values_list('pk', flat=True)],
            **obj.custom_fields,
        )
        return doc

    class Meta:
        date_detection = MetaField('false')


class Directory(Component):
    ip = Keyword()
    href = Keyword()  # @href

    class Index:
        name = 'directory'
        analyzers = [autocomplete_analyzer]

    def get_index_queryset(cls):
        return TagVersion.objects.select_related(
            'tag', 'tag__information_package', 'type',
        ).filter(elastic_index='directory')

    @classmethod
    def from_obj(cls, obj, archive=None):
        units = StructureUnit.objects.filter(tagstructure__tag__versions=obj)

        if archive is not None:
            archive_doc = InnerArchiveDocument.from_obj(archive)
        elif obj.get_root() is not None:
            archive_doc = InnerArchiveDocument.from_obj(obj.get_root())
        else:
            archive_doc = None

        if obj.tag.task is None:
            task_id = None
        else:
            task_id = str(obj.tag.task.pk)

        doc = Directory(
            _id=str(obj.pk),
            id=str(obj.pk),
            task_id=task_id,
            archive=archive_doc,
            structure_units=[ComponentStructureUnitDocument.from_obj(unit) for unit in units],
            current_version=obj.tag.current_version == obj,
            name=obj.name,
            desc=obj.description,
            reference_code=obj.reference_code,
            type=obj.type.name,
            ip=str(obj.tag.information_package.pk),
            agents=[str(pk) for pk in obj.agents.values_list('pk', flat=True)],
            **obj.custom_fields,
        )
        return doc

    class Meta:
        date_detection = MetaField('false')


class StructureUnitDocument(DocumentBase):
    id = Keyword()
    task_id = Keyword()
    name = Text(
        analyzer=autocomplete_analyzer,
        search_analyzer='standard',
        fields={'keyword': {'type': 'keyword'}}
    )
    type = Keyword()
    description = Text()
    comment = Text()
    reference_code = Text(
        analyzer=autocomplete_analyzer,
        search_analyzer='standard',
        fields={'keyword': {'type': 'keyword'}}
    )
    archive = Nested(InnerArchiveDocument)
    start_date = Date()
    end_date = Date()

    @classmethod
    def get_model(cls):
        return StructureUnit

    @classmethod
    def get_index_queryset(cls):
        return StructureUnit.objects.filter(structure__is_template=False)

    @classmethod
    def from_obj(cls, obj):
        structure_set = obj.structure.tagstructure_set
        archive_doc = None
        if structure_set.exists():
            archive = structure_set.first().get_root().tag.current_version
            if archive is not None:
                archive_doc = InnerArchiveDocument.from_obj(archive)

        if obj.task is None:
            task_id = None
        else:
            task_id = str(obj.task.pk)

        doc = StructureUnitDocument(
            _id=obj.pk,
            id=obj.pk,
            task_id=task_id,
            name=obj.name,
            type=obj.type.name,
            description=obj.description,
            comment=obj.comment,
            reference_code=obj.reference_code,
            archive=archive_doc,
            start_date=obj.start_date,
            end_date=obj.end_date,
        )
        return doc

    class Index:
        name = 'structure_unit'
        analyzers = [autocomplete_analyzer]
