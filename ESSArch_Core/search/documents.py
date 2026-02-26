import logging
import os
import time

import elasticsearch_dsl as es
from django.conf import settings
from elasticsearch import (
    ConnectionError,
    RequestError,
    TransportError,
    helpers as es_helpers,
)
from elasticsearch_dsl.connections import get_connection as get_es_connection

from ESSArch_Core.search.alias_migration import migrate
from ESSArch_Core.util import pretty_size


class DocumentBase(es.Document):
    @classmethod
    def get_model(cls):
        raise NotImplementedError

    @classmethod
    def from_obj(cls, obj):
        raise NotImplementedError

    @classmethod
    def from_queryset(cls, qs, to_dict=False):
        for obj in qs:
            if to_dict:
                yield cls.from_obj(obj).to_dict(include_meta=True)
            else:
                yield cls.from_obj(obj)

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
    def index_documents(cls, batch_size=None, remove_stale=False, index_file_content=False, queryset=None):
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
            cls.perform_index(queryset, batch_size, index_file_content)

        # remove the stale values.
        if remove_stale:
            cls.remove_stale(queryset, batch_size)

    @classmethod
    def perform_index(cls, queryset, batch_size, index_file_content=False):
        """
        Performs the indexing.
        """
        logger = logging.getLogger('essarch.search.documents.DocumentBase')
        num = queryset.count()
        logger.debug('Perform bulk index for {} objects with batch_size: {}'.format(num, batch_size))
        conn = get_es_connection()
        for start in range(0, num, batch_size):
            end = start + batch_size
            batch_qs = list(queryset[start:end])

            try:
                batch = cls.create_batch(batch_qs, index_file_content)
                es_helpers.bulk(client=conn, actions=batch)

            except TransportError as e:
                if e.status_code != 413:
                    logger.exception('Elasticsearch transport error during bulk indexing')
                    raise

                logger.error(
                    f'Bulk request too large (413) for batch size {len(batch_qs)}. '
                    'Retrying documents individually.'
                )

                RETRY_WITHOUT_CONTENT_IF_TOO_LARGE = getattr(
                    settings,
                    'ELASTICSEARCH_RETRY_WITHOUT_CONTENT_IF_TOO_LARGE',
                    False
                )

                for obj, action in zip(batch_qs, batch):
                    try:
                        es_helpers.bulk(client=conn, actions=[action])

                    except TransportError as single_error:
                        if single_error.status_code != 413:
                            logger.exception(
                                f'Elasticsearch error indexing document {obj.custom_fields['filename']} ({obj.pk})'
                            )
                            raise

                        logger.warning(
                            f'Document {obj.custom_fields['filename']} ({obj.pk}) too large for individual indexing.'
                        )

                        if index_file_content and RETRY_WITHOUT_CONTENT_IF_TOO_LARGE:
                            logger.info(
                                f'Retrying document {obj.custom_fields['filename']} ({obj.pk}) without file content.'
                            )

                            try:
                                single_batch = cls.create_batch(
                                    [obj],
                                    index_file_content=False
                                )
                                es_helpers.bulk(client=conn, actions=single_batch)

                            except Exception:
                                logger.exception(
                                    f'Retry without content failed for document '
                                    f'{obj.custom_fields['filename']} ({obj.pk})'
                                )
                                raise
                        else:
                            logger.error(
                                f'Not retrying without content for {obj.custom_fields['filename']} '
                                f'({obj.pk}) due to settings'
                            )
                            raise

            except (ConnectionError, RequestError):
                logger.exception('Elasticsearch connection/request error')
                raise

            except Exception:
                logger.exception('Unexpected error indexing')
                raise

            time.sleep(0.3)

    @classmethod
    def create_batch(cls, objects, index_file_content=False):
        """
        Creates the document dict for indexing.
        """
        logger = logging.getLogger('essarch.search')
        MAX_INDEX_SIZE = getattr(settings, 'ELASTICSEARCH_MAX_INDEX_SIZE', None)
        batch = []
        for obj in objects:
            doc = cls.from_obj(obj)
            obj_index_file_content = index_file_content

            if (cls.__name__ == 'File' and obj.tag.information_package and obj_index_file_content and
                    MAX_INDEX_SIZE and obj.custom_fields.get('size', 0) > MAX_INDEX_SIZE):
                logger.info(
                    f'Skipping content indexing due to size for {obj.custom_fields.get("filename", "unknown")} '
                    f'with size {pretty_size(obj.custom_fields.get("size", 0))}')
                obj_index_file_content = False

            if cls.__name__ == 'File' and obj.tag.information_package and obj_index_file_content:
                exclude_file_format_from_indexing_content = settings.EXCLUDE_FILE_FORMAT_FROM_INDEXING_CONTENT
                format_registry_key = obj.custom_fields.get('formatkey', None)
                if format_registry_key not in exclude_file_format_from_indexing_content:
                    ip_file_path = os.path.join(obj.custom_fields['href'], obj.custom_fields['filename'])
                    try:
                        with obj.tag.information_package.open_file(ip_file_path, 'rb') as f:
                            doc = cls.enrich_with_content(doc, file_obj=f)
                        logger.debug('Indexed file content for {} with format registry key {} for ip {}'.format(
                            obj.custom_fields['filename'], format_registry_key, obj.tag.information_package))
                    except NotImplementedError:
                        logger.warning('open_file is not implemented for the information package %s, skip to index '
                                       'file content for %s', obj.tag.information_package, ip_file_path)
                else:
                    logger.warning('Skip to index file content for {} with format registry key {} for ip {}'.format(
                        obj.custom_fields['filename'], format_registry_key, obj.tag.information_package))

            batch.append(doc.to_dict(include_meta=True))
        return batch

    @classmethod
    def remove_stale(cls, queryset, batch_size):
        """
        Removes documents that are present in the index but not in the db.
        Index meta id and db instance pk needs to be same.
        """

        db_ids = list(str(obj_id) for obj_id in queryset.values_list('id', flat=True))
        s = cls.search()
        resp = s.execute()
        total_index = resp.hits.total['value']
        removed = []
        for start in range(0, total_index, batch_size):
            end = start + batch_size
            items = resp.hits[start:end]
            for item in items:
                if str(item.meta.id) not in db_ids:
                    removed.append(item.meta.id)
        for remove_id in removed:
            cls.get(id=remove_id).delete()

        time.sleep(0.5)
