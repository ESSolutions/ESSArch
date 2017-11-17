from elasticsearch_dsl import analyzer, tokenizer, DocType, Date, Keyword, Object, Text

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

class Process(Tag):
    class Meta:
        index = 'tags'

class SubProcess(Tag):
    class Meta:
        index = 'tags'
