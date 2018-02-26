from elasticsearch_dsl import analyzer, tokenizer, DocType, InnerDoc, MetaField, Date, Integer, Long, Keyword, Object, Text, Nested

ngram_tokenizer=tokenizer('custom_ngram_tokenizer', type='ngram', min_gram=1,
                          max_gram=15)
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


class Component(DocType):
    reference_code = Keyword()
    unit_ids = Nested()  # unitid
    unit_dates = Nested()  # unitdate
    name = Text(analyzer=ngram_analyzer, search_analyzer='standard')  # unittitle
    desc = Text(analyzer=ngram_analyzer, search_analyzer='standard')  # e.g. from <odd>
    type = Keyword()  # series, volume, etc.
    parent = Object(Node)
    related = Keyword()  # list of ids for components describing same element in other archive/structure
    archive = Keyword()
    institution = Keyword()
    organization = Keyword()

    class Meta:
        index = 'component'


class Archive(DocType):
    reference_code = Keyword()
    unit_ids = Nested()  # unitid
    unit_dates = Nested()  # unitdate
    name = Text(analyzer=ngram_analyzer, search_analyzer='standard')  # unittitle
    desc = Text(analyzer=ngram_analyzer, search_analyzer='standard')  # e.g. from <odd>
    type = Keyword()
    institution = Keyword()
    organization = Keyword()

    class Meta:
        index = 'archive'


class InformationPackage(DocType):
    id = Keyword()  # @id
    object_identifier_value = Text(analyzer=ngram_analyzer, search_analyzer='standard')
    name = Text(analyzer=ngram_analyzer, search_analyzer='standard')  # label
    start_date = Date()
    end_date = Date()
    institution = Keyword()
    organization = Keyword()

    class Meta:
        index = 'information_package'


class Document(DocType):
    id = Keyword()  # @id
    ip = Keyword()
    parent = Object(Node)  # component
    reference_code = Keyword()
    archive = Keyword()
    institution = Keyword()
    organization = Keyword()
    name = Text(analyzer=ngram_analyzer, search_analyzer='standard')  # @title in 2002, @linktitle in 3.0
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
