import logging

from django.db.models import OuterRef, Subquery, F
from elasticsearch import helpers as es_helpers
from elasticsearch_dsl import Search
from elasticsearch_dsl.connections import get_connection as get_es_connection
from elasticsearch_dsl import Q as ElasticQ
from lxml import etree

from ESSArch_Core.tags.documents import Component
from ESSArch_Core.tags.models import Tag, TagVersion

logger = logging.getLogger('essarch.search.importers.BaseImporter')


<<<<<<< HEAD
class BaseImporter:
    def __init__(self):
=======
class BaseImporter(object):
    def __init__(self, task):
>>>>>>> origin/tag-agents
        self.xmlparser = etree.XMLParser(remove_blank_text=True)
        self.task = task

    def _get_node_query(self, unitid):
        return [ElasticQ("term", current_version=True),
                ElasticQ("nested", path="unit_ids", query=ElasticQ("match", unit_ids__id=unitid))]

    def get_archive(self, ip):
        raise NotImplementedError

    def get_component(self, unitid):
        query = Component.search().query("bool", must=self._get_node_query(unitid))
        doc = query.execute().hits[0]
        return TagVersion.objects.get(pk=doc._id)

    def import_content(self, path, rootdir=None, ip=None, **extra_paths):
        raise NotImplementedError

    def update_current_tag_versions(self):
        logger.info("Update current tag versions...")

        versions = TagVersion.objects.filter(tag=OuterRef('pk'))
        Tag.objects.filter(
            task=self.task, current_version__isnull=True
        ).annotate(
            version=Subquery(versions.values('pk')[:1])
        ).update(
            current_version_id=F('version')
        )

        logger.info("Updated current tag versions")

    @staticmethod
    def save_to_elasticsearch(components):
        logger.info("Saving to Elasticsearch...")
        conn = get_es_connection()
        count = 0

        for ok, result in es_helpers.streaming_bulk(conn, components):
            action, result = result.popitem()
            doc_id = result['_id']
            doc = '/%s/%s' % (result['_index'], doc_id)

            if not ok:
                logger.error('Failed to %s document %s: %r' % (action, doc, result))
            else:
                logger.debug('Saved document %s: %r' % (doc, result))
                count += 1

            yield ok, count

        logger.info("Documents saved to Elasticsearch")

    @staticmethod
    def cleanup_elasticsearch(task):
        logger.info("Deleting task tags already in Elasticsearch...")
        conn = get_es_connection()
        Search(using=conn, index='_all').query('term', task_id=str(task.pk)).delete()
        logger.info("Deleted task tags already in Elasticsearch")
