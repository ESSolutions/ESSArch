from elasticsearch_dsl import Q as ElasticQ
from lxml import etree

from ESSArch_Core.tags.documents import Archive, Component
from ESSArch_Core.tags.models import TagVersion


class BaseImporter(object):
    def __init__(self):
        self.xmlparser = etree.XMLParser(remove_blank_text=True)

    def _get_tag_query(self, unitid):
        return [ElasticQ("term", current_version=True),
                ElasticQ("nested", path="unit_ids", query=ElasticQ("match", unit_ids__id=unitid))]

    def get_archive(self, unitid):
        query = Archive.search().query("bool", must=self._get_tag_query(unitid))
        doc = query.execute().hits[0]
        return TagVersion.objects.get(pk=doc._id)

    def get_component(self, unitid):
        query = Component.search().query("bool", must=self._get_tag_query(unitid))
        doc = query.execute().hits[0]
        return TagVersion.objects.get(pk=doc._id)

    def import_content(self, rootdir, xmlpath, ip):
        raise NotImplementedError
