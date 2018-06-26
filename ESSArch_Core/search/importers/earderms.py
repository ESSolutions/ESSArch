# -*- coding: utf-8 -*-

import base64
import itertools
import logging
import os
import uuid

import six
from django.db import transaction
from django.db.models import OuterRef, Subquery, F, Q
from lxml import etree
from redis import Redis
from six.moves import cPickle

from ESSArch_Core.search.importers.base import BaseImporter
from ESSArch_Core.tags import INDEX_QUEUE
from ESSArch_Core.tags.documents import Archive, Component, Document, Node
from ESSArch_Core.tags.models import Tag, TagStructure, TagVersion
from ESSArch_Core.util import get_tree_size_and_count, normalize_path, timestamp_to_datetime

logger = logging.getLogger('essarch.search.importers.EardErmsImporter')
redis_conn = Redis()


class EardErmsImporter(BaseImporter):
    def get_archive(self, ip):
        ctsfile = ip.get_content_type_file()
        try:
            tree = etree.parse(ctsfile, self.xmlparser)
            root = tree.getroot()
            archive_id = root.xpath("//*[local-name()='ArkivReferens']")[0].text

            try:
                return TagVersion.objects.get(Q(Q(name=archive_id) | Q(reference_code=archive_id)), elastic_index='archive')
            except TagVersion.DoesNotExist:
                logger.exception(u'"{}" not found'.format(reference))
                raise
        except (IndexError, TagVersion.DoesNotExist):
            pass

        return ip.tag

    def get_component(self, reference, archive):
        archive_tree_id = archive.get_active_structure().tree_id
        try:
            return TagVersion.objects.get(Q(Q(name=reference) | Q(reference_code=reference)), tag__structures__tree_id=archive_tree_id)
        except TagVersion.DoesNotExist:
            logger.exception(u'"{}" not found'.format(reference))
            raise

    def get_errands_root(self, el):
        return el.xpath("*[local-name()='ArkivobjektListaArenden']")

    def get_acts_root(self, el):
        return el.xpath("*[local-name()='ArkivobjektListaHandlingar']")

    def parse_document(self, xmlpath, ip, rootdir, document, act, parent):
        id = str(uuid.uuid4())
        name = document.get("Namn")
        desc = document.get("Beskrivning")
        filepath = normalize_path(os.path.join(ip.get_inner_ip_path(), 'Files', name))
        href = os.path.dirname(os.path.relpath(filepath, rootdir))
        href = '' if href == '.' else href
        filename = os.path.basename(name)
        ext = os.path.splitext(filename)[1][1:]

        with open(filepath, 'rb') as f:
            content = f.read()
            encoded_content = base64.b64encode(content).decode("ascii")

        size, _ = get_tree_size_and_count(filepath)
        modified = timestamp_to_datetime(os.stat(filepath).st_mtime)

        d = Document(_id=id, name=name, type='Bilaga', archive=act.archive, desc=desc, filename=filename, href=href, extension=ext,
                     data=encoded_content, size=size, modified=modified, current_version=True, ip=str(ip.pk))

        tag = Tag(information_package=ip)
        tag_version = TagVersion(pk=d.meta.id, tag=tag,
                                 elastic_index=d.meta.index,
                                 name=d.name, type=d.type,
                                 reference_code='')
        tag_repr = TagStructure(tag=tag, parent=parent, structure=parent.structure, tree_id=parent.tree_id, lft=0, rght=0, level=0)
        self.indexed_files.append(filepath)
        return tag, tag_version, tag_repr, cPickle.dumps(d)

    def parse_person(self, el):
        data = {}
        data_mappings = {
            'namn': 'Namn',
            'organisation': 'Organisation',
            'postadress': 'Postadress',
            'postnummer': 'Postnummer',
            'postort': 'Postort',
            'land': 'Lang',
            'id': 'IDnummer',
            'telefon': 'Telefon',
            'fax': 'Fax',
            'epost': 'EPost',
            'skyddad_identitet': 'SkyddadIdentitet',
        }

        for k, v in six.iteritems(data_mappings):
            try:
                data[k] = el.xpath("*[local-name()='{el}']".format(el=v))[0].text
            except IndexError:
                continue

        return data

    def parse_agent(self, el):
        data = {}
        data_mappings = {
            'namn': 'Namn',
            'roll': 'Roll',
            'enhet': 'Enhetsnamn',
            'organisation': 'Organisationsnamn',
        }

        for k, v in six.iteritems(data_mappings):
            try:
                data[k] = el.xpath("*[local-name()='{el}']".format(el=v))[0].text
            except IndexError:
                continue

        return data

    def parse_relation(self, el):
        return {
            'typ': el.get('AnnanTyp') if el.get('Typ') == 'Egen relationsdefinition' else el.get('Typ'),
            'referens': el.text
        }

    def parse_initiator(self, el):
        initiator_obj = {}
        value_map = {
            'name': 'Namn',
            'address': 'Adress',
            'zipcode': 'Postnummer',
            'city': 'Postort',
            'personal_identification_number': 'Personnummer',
            'phone': 'Telefon',
            'mobile_phone': 'Mobil',
            'email': 'E-post',
        }

        for k,v in six.iteritems(value_map):
            try:
                initiator_obj[k] = el.xpath("*/*[local-name()='Egenskap' and @Namn='%s']" % v)[0].xpath("*[local-name()='Varde']")[0].text
            except IndexError:
                pass

        return initiator_obj

    def parse_restriction(self, el):
        data = {}
        data_mappings = {
            'beskrivning': 'ForklarandeText',
            'lagrum': 'Lagrum',
            'upphor': 'RestriktionsDatum',
        }

        for k, v in six.iteritems(data_mappings):
            try:
                data[k] = el.xpath("*[local-name()='{el}']".format(el=v))[0].text
            except IndexError:
                continue

        typ = el.xpath("./@*[local-name()='Typ']")[0]
        try:
            annan_typ = el.xpath("./@*[local-name()='AnnanTyp']")[0]
        except IndexError:
            pass
        else:
            typ = annan_typ

        data['typ'] = six.text_type(typ)
        return data

    def parse_act(self, act, errand):
        id = str(uuid.uuid4())#act.get("Systemidentifierare")
        reference_code = act.xpath("*[local-name()='ArkivobjektID']")[0].text
        unit_ids = {'id': reference_code}
        parent = Node(id=errand._id, index=errand._index)

        data = {}
        data_mappings = {
            'name': ['Rubrik', 'ArkivobjektID'],
            'status': 'StatusHandling',
            'handlingstyp': 'Handlingstyp',
        }

        for k, v in six.iteritems(data_mappings):
            if not isinstance(v, list):
                v = [v]
            found = False
            for val in v:
                if not found:
                    try:
                        data[k] = act.xpath("*[local-name()='{el}']".format(el=val))[0].text
                    except IndexError:
                        continue
                    else:
                        found = True

        try:
            avsandare = act.xpath("*[local-name()='Avsandare']")[0]
            data['avsandare'] = self.parse_person(avsandare)
        except IndexError:
            pass

        data['agenter'] = []
        for agent in act.xpath("*[local-name()='Agent']"):
            data['agenter'].append(self.parse_agent(agent))

        data['restriktioner'] = []
        for restriktion in act.xpath("*[local-name()='Restriktion']"):
            data['restriktioner'].append(self.parse_restriction(restriktion))

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

        data.update(dates)
        return Component(_id=id, current_version=True, unit_ids=unit_ids, parent=parent, type='Handling', reference_code=reference_code, archive=errand.archive, **data)

    def parse_mappings(self, mappings, el):
        data = {}
        for k, v in six.iteritems(mappings):
            if not isinstance(v, list):
                v = [v]
            found = False
            for val in v:
                if not found:
                    try:
                        data[k] = el.xpath("*[local-name()='{el}']".format(el=val))[0].text
                    except IndexError:
                        continue
                    else:
                        found = True
        return data

    def parse_acts(self, xmlpath, ip, rootdir, errand, acts_root, parent):
        for act_el in acts_root.xpath("*[local-name()='ArkivobjektHandling']"):
            act = self.parse_act(act_el, errand)
            act.ip = str(ip.pk)

            tag = Tag(information_package=ip)
            tag_version = TagVersion(pk=act.meta.id, tag=tag,
                                     elastic_index=act.meta.index,
                                     name=act.name, type=act.type,
                                     reference_code=act.reference_code)
            tag_repr = TagStructure(tag=tag, parent=parent, structure=parent.structure, tree_id=parent.tree_id, lft=0, rght=0, level=0)

            for doc_el in act_el.xpath("*[local-name()='Bilaga']"):
                yield self.parse_document(xmlpath, ip, rootdir, doc_el, act, tag_repr)

            yield tag, tag_version, tag_repr, cPickle.dumps(act)

    def parse_errand(self, errand, archive):
        id = str(uuid.uuid4())#errand.get("Systemidentifierare")
        reference_code = errand.xpath("*[local-name()='ArkivobjektID']")[0].text
        unit_ids = {'id': reference_code}
        parent_reference_code = errand.xpath("*[local-name()='KlassReferens']")[0].text
        try:
            parent = self.get_component(parent_reference_code, archive)
        except TagVersion.DoesNotExist:
            # the referenced element doesn't exist, create a dummy
            parent_id = str(uuid.uuid4())
            try:
                parent_name = errand.xpath("*[local-name()='Klass']")[0].text
            except IndexError:
                parent_name = ''

            tag = Tag.objects.create()
            parent = TagVersion.objects.create(pk=parent_id, tag=tag,
                                               elastic_index='component',
                                               reference_code=parent_reference_code,
                                               name=parent_name, type=u'Process')
            archive_structure = archive.get_active_structure()
            tag_repr = TagStructure.objects.create(tag=tag, parent=archive_structure, structure=archive_structure.structure, tree_id=archive_structure.tree_id, lft=0, rght=0, level=0)

        parent = Node(id=str(parent.pk), index=parent.elastic_index)

        data_mappings = {
            'name': ['Arendemening', 'Rubrik', 'ArkivobjektID'],
            'status': 'StatusArande',
            'arendetyp': 'ArendeTyp',
        }
        data = self.parse_mappings(data_mappings, errand)

        try:
            motpart = errand.xpath("*[local-name()='Motpart']")[0]
            data['motpart'] = self.parse_person(motpart)
        except IndexError:
            pass

        data['relationer'] = []
        for relation in errand.xpath("*[local-name()='ArendeRelation']"):
            data['relationer'].append(self.parse_relation(relation))


        data['agenter'] = []
        for agent in errand.xpath("*[local-name()='Agent']"):
            data['agenter'].append(self.parse_agent(agent))

        data['restriktioner'] = []
        for restriktion in errand.xpath("*[local-name()='Restriktion']"):
            data['restriktioner'].append(self.parse_restriction(restriktion))

        date_mappings = {
            'decision_date': 'Beslutat',
            'dispatch_date': 'Expedierad',
            'arrival_date': 'Inkommen',
            'last_usage_date': 'SistaAnvandandetidpunkt',
            'create_date': 'Skapad',
            'preparation_date': 'Upprattad',
            'ended_date': 'Avslutat',
        }
        dates = self.parse_mappings(date_mappings, errand)

        personal_identification_numbers = []
        initiators = []
        for initiator in errand.xpath("*/*[local-name()='EgetElement' and @Namn='Initierare']"):
            initiator_obj = self.parse_initiator(initiator)
            initiators.append(initiator_obj)
            try:
                personal_identification_numbers.append(initiator_obj['personal_identification_number'])
            except KeyError:
                pass

        data.update(dates)
        return Component(_id=id, current_version=True, unit_ids=unit_ids, parent=parent, type=u'Ärende', reference_code=reference_code, **data)

    def get_tag_structure(self, tag_version_id):
        return TagStructure.objects.filter(tag__versions__pk=tag_version_id).latest()

    def parse_errands(self, xmlpath, ip, rootdir, archive, errands_root):
        for errand in errands_root.xpath("*[local-name()='ArkivobjektArende']"):
            component = self.parse_errand(errand, archive)
            component.ip = str(ip.pk)
            component.archive = str(archive.pk)
            tag = Tag(information_package=ip)
            tag_version = TagVersion(pk=component.meta.id, tag=tag,
                                     elastic_index=component.meta.index,
                                     name=component.name, type=component.type,
                                     reference_code=component.reference_code)
            parent = self.get_tag_structure(component.parent.id)
            tag_repr = TagStructure(tag=tag, parent=parent, structure=parent.structure, tree_id=parent.tree_id, lft=0, rght=0, level=0)

            acts_root = self.get_acts_root(errand)
            if len(acts_root):
                for act in self.parse_acts(xmlpath, ip, rootdir, component, acts_root[0], tag_repr):
                    yield act

            yield tag, tag_version, tag_repr, cPickle.dumps(component)

    def import_content(self, ip):
        self.indexed_files = []
        ctsfile = ip.get_content_type_file()

        tree = etree.parse(ctsfile, self.xmlparser)
        root = tree.getroot()

        archive = self.get_archive(ip).tag.current_version
        errands_root = self.get_errands_root(root)

        if len(errands_root):
            with transaction.atomic():
                with TagStructure.objects.disable_mptt_updates():
                    tags, tag_versions, tag_reprs, components = itertools.izip(*self.parse_errands(ctsfile, ip, ip.object_path, archive, errands_root[0]))

                    Tag.objects.bulk_create(reversed(tags), batch_size=1000)
                    TagVersion.objects.bulk_create(reversed(tag_versions), batch_size=1000)
                    TagStructure.objects.bulk_create(reversed(tag_reprs), batch_size=1000)

                    versions = TagVersion.objects.filter(tag=OuterRef('pk'))
                    Tag.objects.annotate(version=Subquery(versions.values('pk')[:1])).update(current_version_id=F('version'))

                    redis_conn.rpush(INDEX_QUEUE, *components)

        TagStructure.objects.partial_rebuild(archive.get_active_structure().tree_id)
        return self.indexed_files
