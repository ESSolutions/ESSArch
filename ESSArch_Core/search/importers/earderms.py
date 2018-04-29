import base64
import cPickle
import itertools
import os
import uuid

import six
from django.db import transaction
from django.db.models import OuterRef, Subquery, F
from elasticsearch_dsl import Q as ElasticQ
from lxml import etree
from redis import Redis

from ESSArch_Core.tags import INDEX_QUEUE
from ESSArch_Core.tags.documents import Archive, Component, Document, Node
from ESSArch_Core.tags.models import Tag, TagStructure, TagVersion
from ESSArch_Core.util import get_tree_size_and_count, normalize_path, timestamp_to_datetime

redis_conn = Redis()


class EardErmsImporter(object):
    def __init__(self):
        self.xmlparser = etree.XMLParser(remove_blank_text=True)

    def get_archive(self, unitid):
        query = Archive.search().query("bool", must=[ElasticQ("term", current_version=True),
                                                     ElasticQ("nested", path="unit_ids",
                                                              query=ElasticQ("match", unit_ids__id=unitid))])
        doc = query.execute().hits[0]
        return TagVersion.objects.get(pk=doc._id)

    def get_component(self, unitid):
        query = Component.search().query("bool", must=[ElasticQ("term", current_version=True),
                                                       ElasticQ("nested", path="unit_ids",
                                                                query=ElasticQ("match", unit_ids__id=unitid))])
        doc = query.execute().hits[0]
        return TagVersion.objects.get(pk=doc._id)

    def get_errands_root(self, el):
        return el.xpath("*[local-name()='ArkivobjektListaArenden']")

    def get_acts_root(self, el):
        return el.xpath("*[local-name()='ArkivobjektListaHandlingar']")

    def parse_document(self, document, act, parent):
        id = str(uuid.uuid4())
        name = document.get("Namn")
        desc = document.get("Beskrivning")
        path = normalize_path(document.get("Lank"))
        filepath = os.path.realpath(os.path.join(os.path.dirname(self.xmlpath), path))
        href = os.path.dirname(os.path.relpath(filepath, self.rootdir))
        href = '' if href == '.' else href
        filename = os.path.basename(path)
        ext = os.path.splitext(filename)[1][1:]

        with open(filepath, 'rb') as f:
            content = f.read()
            encoded_content = base64.b64encode(content).decode("ascii")

        size, _ = get_tree_size_and_count(filepath)
        modified = timestamp_to_datetime(os.stat(filepath).st_mtime)

        d = Document(_id=id, name=name, type='document', desc=desc, filename=filename, href=href, extension=ext,
                     data=encoded_content, size=size, modified=modified, current_version=True, ip=str(self.ip.pk))

        tag = Tag(information_package=self.ip)
        tag_version = TagVersion(pk=d.meta.id, tag=tag,
                                 elastic_index=d.meta.index,
                                 name=d.name, type=d.type)
        tag_repr = TagStructure(tag=tag, parent=parent, structure=parent.structure, tree_id=parent.tree_id, lft=0, rght=0, level=0)
        self.indexed_files.append(filepath)
        return tag, tag_version, tag_repr, cPickle.dumps(d)

    def parse_act(self, act, errand):
        id = act.get("Systemidentifierare")
        reference_code = act.xpath("*[local-name()='ArkivobjektID']")[0].text
        unit_ids = {'id': reference_code}
        name = act.xpath("*[local-name()='Beskrivning']")[0].text
        type = act.xpath("*[local-name()='Handlingstyp']")[0].text
        parent = Node(id=errand._id, index=errand._index)

        date_mappings = {
            'dispatch_date': 'Expedierad',
            'arrival_date': 'Inkommen',
            'last_usage_date': 'SistaAnvandandetidpunkt',
            'create_date': 'Skapad',
            'preparation_date': 'Upprattad',
        }
        dates = {}

        for k, v in six.iteritems(date_mappings):
            try:
                dates[k] = act.xpath("*[local-name()='{el}']".format(el=v))[0].text
            except IndexError:
                continue

        return Component(_id=id, current_version=True, unit_ids=unit_ids, parent=parent, name=name, type=type, **dates)

    def parse_acts(self, errand, acts_root, parent):
        for act_el in acts_root.xpath("*[local-name()='ArkivobjektHandling']"):
            act = self.parse_act(act_el, errand)

            tag = Tag()
            tag_version = TagVersion(pk=act.meta.id, tag=tag,
                                     elastic_index=act.meta.index,
                                     name=act.name, type=act.type)
            tag_repr = TagStructure(tag=tag, parent=parent, structure=parent.structure, tree_id=parent.tree_id, lft=0, rght=0, level=0)

            for doc_el in act_el.xpath("*[local-name()='Bilaga']"):
                yield self.parse_document(doc_el, act, tag_repr)

            yield tag, tag_version, tag_repr, cPickle.dumps(act)

    def parse_errand(self, errand):
        id = errand.get("Systemidentifierare")
        reference_code = errand.xpath("*[local-name()='Klass']")[0].text
        unit_ids = {'id': reference_code}
        name = errand.xpath("*[local-name()='Arendemening']")[0].text
        type = errand.xpath("*[local-name()='ArendeTyp']")[0].text
        parent = self.get_component(reference_code)
        parent = Node(id=str(parent.pk), index=parent.elastic_index)

        date_mappings = {
            'decision_date': 'Beslutat',
            'dispatch_date': 'Expedierad',
            'arrival_date': 'Inkommen',
            'last_usage_date': 'SistaAnvandandetidpunkt',
            'create_date': 'Skapad',
            'preparation_date': 'Upprattad',
        }
        dates = {}

        for k, v in six.iteritems(date_mappings):
            try:
                dates[k] = errand.xpath("*[local-name()='{el}']".format(el=v))[0].text
            except IndexError:
                continue

        return Component(_id=id, current_version=True, unit_ids=unit_ids, parent=parent, name=name, type=type, **dates)

    def get_tag_structure(self, tag_version_id):
        return TagStructure.objects.get(tag__versions__pk=tag_version_id)

    def parse_errands(self, archive, errands_root):
        for errand in errands_root.xpath("*[local-name()='ArkivobjektArende']"):
            component = self.parse_errand(errand)
            component.archive = str(archive.pk)
            tag = Tag()
            tag_version = TagVersion(pk=component.meta.id, tag=tag,
                                     elastic_index=component.meta.index,
                                     name=component.name, type=component.type)
            parent = self.get_tag_structure(component.parent.id)
            tag_repr = TagStructure(tag=tag, parent=parent, structure=parent.structure, tree_id=parent.tree_id, lft=0, rght=0, level=0)

            acts_root = self.get_acts_root(errand)
            if len(acts_root):
                for act in self.parse_acts(component, acts_root[0], tag_repr):
                    yield act

            yield tag, tag_version, tag_repr, cPickle.dumps(component)

    def import_content(self, rootdir, xmlpath, ip):
        self.rootdir = rootdir
        self.xmlpath = xmlpath
        self.ip = ip
        self.indexed_files = []

        tree = etree.parse(self.xmlpath, self.xmlparser)
        root = tree.getroot()

        archive = root.xpath("*[local-name()='VerksamhetsbaseradArkivredovisning']")[0]
        archive_unitid = archive.xpath("*[local-name()='ArkivReferens']")[0].text
        archive = self.get_archive(archive_unitid)
        errands_root = self.get_errands_root(root)

        if len(errands_root):
            with transaction.atomic():
                with TagStructure.objects.disable_mptt_updates():
                    tags, tag_versions, tag_reprs, components = itertools.izip(*self.parse_errands(archive, errands_root[0]))

                    Tag.objects.bulk_create(reversed(tags), batch_size=1000)
                    TagVersion.objects.bulk_create(reversed(tag_versions), batch_size=1000)
                    TagStructure.objects.bulk_create(reversed(tag_reprs), batch_size=1000)

                    versions = TagVersion.objects.filter(tag=OuterRef('pk'))
                    Tag.objects.annotate(version=Subquery(versions.values('pk')[:1])).update(current_version_id=F('version'))

                    redis_conn.rpush(INDEX_QUEUE, *components)

        TagStructure.objects.partial_rebuild(archive.get_active_structure().tree_id)
        return self.indexed_files
