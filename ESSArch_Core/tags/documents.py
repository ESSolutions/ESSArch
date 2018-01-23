from elasticsearch_dsl import analyzer, tokenizer, DocType, MetaField, Date, Integer, Keyword, Object, Text, Nested

ngram_tokenizer=tokenizer('custom_ngram_tokenizer', type='ngram', min_gram=1,
                          max_gram=15, token_chars=['letter', 'digit',
                                                    'punctuation', 'symbol'])
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


class Component(DocType):
    reference_code = Keyword()
    unit_ids = Nested()  # unitid
    unit_dates = Nested()  # unitdate
    name = Text(analyzer=ngram_analyzer, search_analyzer='standard')  # unittitle
    desc = Text(analyzer=ngram_analyzer, search_analyzer='standard')  # e.g. from <odd>
    type = Keyword()  # series, volume, etc.
    parent = Keyword()
    related = Keyword()  # list of ids for components describing same element in other archive/structure
    archive = Keyword()

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


class Document(DocType):
    id = Keyword()  # @id
    ip = Keyword()
    component = Keyword()
    archive = Keyword()
    institution = Keyword()
    organization = Keyword()
    name = Text(analyzer=ngram_analyzer, search_analyzer='standard')  # @title in 2002, @linktitle in 3.0
    href = Keyword()  # @href

    class Meta:
        index = 'document'
