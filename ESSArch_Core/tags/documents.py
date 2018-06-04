from django.utils import timezone
from elasticsearch_dsl import (Boolean, Date, DocType, InnerDoc, Integer, Keyword, Long,
                               Nested, Object, Q, Text, analyzer,
                               tokenizer)

ngram_tokenizer=tokenizer('custom_ngram_tokenizer', type='ngram', min_gram=3,
                          max_gram=3)
ngram_analyzer = analyzer('custom_ngram_analyzer', tokenizer=ngram_tokenizer,
                          filter=['lowercase'])


class Tag(DocType):
    name = Text(analyzer=ngram_analyzer, search_analyzer='standard')
    desc = Text()
    parents = Object()
    reference_code = Keyword()
    start_date = Date()
    end_date = Date()

    class Meta:
        index = 'tags'


class Archive(Tag):
    class Meta:
        index = 'tags'


class Series(Tag):
    class Meta:
        index = 'tags'


class Volume(Tag):
    class Meta:
        index = 'tags'

class Activity(Tag):
    class Meta:
        index = 'tags'

class ProcessGroup(Tag):
    class Meta:
        index = 'tags'

class Process(Tag):
    class Meta:
        index = 'tags'

class Document(Tag):
    terms_and_condition = Keyword()
    class Meta:
        index = 'tags'


class Node(InnerDoc):
    id = Keyword()
    index = Keyword()


class VersionedDocType(DocType):
    link_id = Keyword()
    current_version = Boolean()
    index_date = Date()

    def create_new_version(self, start_date=None, end_date=None, refresh=False):
        data = self.to_dict(include_meta=False)
        data['_index'] = self.meta.index
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
        index = self.meta.index
        versions = self.__class__.search(index=index).source(False).query(
            'bool', must=[Q('term', link_id=self.link_id)], must_not=[Q('term', _id=self._id)]
        ).execute()

        for version in versions:
            version.update(current_version=False)

        self.update(current_version=True)


class Component(VersionedDocType):
    reference_code = Keyword()
    unit_ids = Nested()  # unitid
    unit_dates = Nested()  # unitdate
    name = Text(analyzer=ngram_analyzer, fields={'keyword': {'type': 'keyword'}})  # unittitle
    arrival_date = Date()
    decision_date = Date()
    preparation_date = Date()
    create_date = Date()
    dispatch_date = Date()
    last_usage_date = Date()
    desc = Text(analyzer=ngram_analyzer)  # e.g. from <odd>
    type = Keyword()  # series, volume, etc.
    parent = Object(Node)
    archive = Keyword()
    institution = Keyword()
    organization = Keyword()

    class Meta:
        index = 'component'


class Archive(VersionedDocType):
    reference_code = Keyword()
    unit_ids = Nested()  # unitid
    unit_dates = Nested()  # unitdate
    name = Text(analyzer=ngram_analyzer, fields={'keyword': {'type': 'keyword'}})  # unittitle
    desc = Text(analyzer=ngram_analyzer)  # e.g. from <odd>
    type = Keyword()
    institution = Keyword()
    organization = Keyword()
    organization_group = Integer()

    class Meta:
        index = 'archive'


class InformationPackage(DocType):
    id = Keyword()  # @id
    object_identifier_value = Text(analyzer=ngram_analyzer, search_analyzer='standard', fields={'keyword': {'type': 'keyword'}})
    name = Text(analyzer=ngram_analyzer, search_analyzer='standard', fields={'keyword': {'type': 'keyword'}})  # label
    start_date = Date()
    end_date = Date()
    institution = Keyword()
    organization = Keyword()

    class Meta:
        index = 'information_package'


class Document(Component):
    ip = Keyword()
    filename = Keyword()
    extension = Keyword()
    href = Keyword()  # @href
    size = Long()
    modified = Date()

    class Meta:
        index = 'document'


class Directory(DocType):
    ip = Keyword()
    name = Keyword()
    href = Keyword()  # @href

    class Meta:
        index = 'directory'
