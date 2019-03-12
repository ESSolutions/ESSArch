from elasticsearch_dsl import (Date, InnerDoc, Keyword, Nested, Text)

from ESSArch_Core.agents.models import Agent
from ESSArch_Core.search.documents import DocumentBase
from ESSArch_Core.tags.documents import autocomplete_analyzer


class AgentNameDocument(InnerDoc):
    main = Text()
    part = Text()
    description = Text()
    start_date = Date()
    end_date = Date()

    @classmethod
    def from_obj(cls, obj):
        doc = AgentNameDocument(
            main=obj.main,
            part=obj.part,
            description=obj.description,
            start_date=obj.start_date,
            end_date=obj.end_date,
        )
        return doc


class AgentDocument(DocumentBase):
    id = Keyword()
    task_id = Keyword()
    names = Nested(AgentNameDocument)
    start_date = Date()
    end_date = Date()

    @classmethod
    def get_model(cls):
        return Agent

    @classmethod
    def from_obj(cls, obj):
        doc = AgentDocument(
            _id=str(obj.pk),
            id=str(obj.pk),
            task_id=str(obj.task.pk),
            names=[
                AgentNameDocument.from_obj(name) for name in obj.names.iterator()
            ],
            start_date=obj.start_date,
            end_date=obj.end_date,
        )
        return doc

    class Index:
        name = 'agent'
        analyzers = [autocomplete_analyzer]
