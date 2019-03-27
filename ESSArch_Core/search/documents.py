import logging
import time

from django.conf import settings

import elasticsearch_dsl as es
from elasticsearch import helpers as es_helpers
from elasticsearch_dsl.connections import get_connection as get_es_connection

from ESSArch_Core.search.alias_migration import migrate


logger = logging.getLogger('essarch.search.documents.DocumentBase')


class DocumentBase(es.Document):
    @classmethod
    def get_model(cls):
        raise NotImplementedError

    @classmethod
    def from_obj(cls, obj):
        raise NotImplementedError

    @classmethod
    def get_index_queryset(cls):
        """
        Base queryset for indexing the document.
        """

        return cls.get_model().objects.all()

    @classmethod
    def clear_index(cls):
        """
        Clears the index, makes a new empty one and repoints alias
        """

        migrate(cls, move_data=False, update_alias=True, delete_old_index=True)

    @classmethod
    def index_documents(cls, batch_size=None, remove_stale=False, queryset=None):
        """
        Main method for indexing the documents.
        """

        if not batch_size:
            batch_size = settings.ELASTICSEARCH_BATCH_SIZE

        # base queryset for indexing the docs.
        if queryset is None:
            queryset = cls().get_index_queryset()

        # perform the indexing
        if queryset:
            cls.perform_index(queryset, batch_size)

        # remove the stale values.
        if remove_stale:
            cls.remove_stale(queryset, batch_size)

    @classmethod
    def perform_index(cls, queryset, batch_size):
        """
        Performs the indexing.
        """

        for start in range(0, queryset.count(), batch_size):
            end = start + batch_size
            batch_qs = queryset[start:end]
            batch = cls.create_batch(list(batch_qs))
            cls.index_batch(batch)
            time.sleep(0.5)

    @classmethod
    def create_batch(cls, objects):
        """
        Creates the document dict for indexing.
        """

        batch = []
        for obj in objects:
            batch.append(cls.from_obj(obj).to_dict(include_meta=True))
        return batch

    @classmethod
    def index_batch(cls, batch):
        """
        Index the specified batch.
        """

        conn = get_es_connection()
        es_helpers.bulk(client=conn, actions=batch)

    @classmethod
    def remove_stale(cls, queryset, batch_size):
        """
        Removes documents that are present in the index but not in the db.
        Index meta id and db instance pk needs to be same.
        """

        db_ids = list(queryset.values_list('id', flat=True))
        s = cls.search()
        resp = s.execute()
        total_index = resp.hits.total
        removed = []
        for start in range(0, total_index, batch_size):
            end = start + batch_size
            items = resp.hits[start:end]
            for item in items:
                if item.meta.id not in db_ids:
                    removed.append(item.meta.id)
        for remove_id in removed:
            cls.get(id=remove_id).delete()
