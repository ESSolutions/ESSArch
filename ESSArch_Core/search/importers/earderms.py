# -*- coding: utf-8 -*-

import base64
import errno
import logging
import os
import uuid

from django.db import transaction
from django.db.models import Q
from lxml import etree

from ESSArch_Core.search.importers.base import BaseImporter
from ESSArch_Core.tags.documents import Component, File
from ESSArch_Core.tags.models import (
    StructureUnit,
    Tag,
    TagStructure,
    TagVersion,
    TagVersionType,
)
from ESSArch_Core.util import (
    get_tree_size_and_count,
    remove_prefix,
    timestamp_to_datetime,
)

logger = logging.getLogger('essarch.search.importers.EardErmsImporter')


def get_encoded_content_from_file(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
        encoded_content = base64.b64encode(content).decode("ascii")
    return encoded_content


class EardErmsImporter(BaseImporter):
    def get_archive(self, xmlfile):
        try:
            tree = etree.parse(xmlfile, self.xmlparser)
            root = tree.getroot()
            archive_id = root.xpath("//*[local-name()='ArkivReferens']")[0].text

            try:
                return TagVersion.objects.get(
                    Q(Q(name=archive_id) | Q(reference_code=archive_id)), elastic_index='archive'
                )
            except TagVersion.DoesNotExist:
                logger.exception('"{}" not found'.format(archive_id))
                raise
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
        except (IndexError, TagVersion.DoesNotExist):
            pass

        return None

    def get_component(self, reference, archive):
        archive_tree_id = archive.get_active_structure().tree_id
        try:
            return TagVersion.objects.get(
                Q(Q(name=reference) | Q(reference_code=reference)), tag__structures__tree_id=archive_tree_id
            )
        except TagVersion.DoesNotExist:
            logger.exception('"{}" not found'.format(reference))
            raise

    def get_errands_root(self, el):
        return el.xpath("*[local-name()='ArkivobjektListaArenden']")

    def get_arkiv_objekt_arenden(self, el):
        return el.xpath("*[local-name()='ArkivobjektArende']")

    def get_acts_root(self, el):
        return el.xpath("*[local-name()='ArkivobjektListaHandlingar']")

    def parse_document(self, ip, rootdir, document, act, parent, archive):
        id = str(uuid.uuid4())
        name = document.get("Namn")
        desc = document.get("Beskrivning")

        filepath = document.get('Lank')
        if ip is not None:
            filepath = os.path.join(ip.object_path, ip.sip_path, document.get('Lank'))
        elif rootdir is not None:
            filepath = os.path.join(rootdir, document.get('Lank'))

        href = os.path.dirname(os.path.relpath(filepath, rootdir))
        href = '' if href == '.' else href
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filepath)[1][1:]

        encoded_content = get_encoded_content_from_file(filepath)

        size, _ = get_tree_size_and_count(filepath)
        modified = timestamp_to_datetime(os.stat(filepath).st_mtime)

        custom_fields = {
            'filename': filename,
            'href': href,
            'extension': ext,
            'size': size,
            'modified': modified,
        }

        tag = Tag.objects.create(information_package=ip, task=self.task)
        tag_version_type, _ = TagVersionType.objects.get_or_create(name='Bilaga')
        tag_version = TagVersion.objects.create(
            pk=id,
            tag=tag,
            elastic_index='document',
            name=name,
            description=desc,
            type=tag_version_type,
            reference_code='',
            custom_fields=custom_fields,
        )
        tag_repr = TagStructure.objects.create(
            tag=tag,
            parent=parent,
            structure=parent.structure,
            tree_id=parent.tree_id,
            lft=0,
            rght=0,
            level=0,
        )
        self.indexed_files.append(filepath)

        d = File.from_obj(tag_version, archive)
        d.data = encoded_content
        d_dict = d.to_dict(include_meta=True)
        d_dict['pipeline'] = 'ingest_attachment'
        return tag, tag_version, tag_repr, d_dict

    def parse_person(self, el):
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

        data = self.parse_mappings(data_mappings, el)
        return data

    def parse_agent(self, el):
        data_mappings = {
            'namn': 'Namn',
            'roll': 'Roll',
            'enhet': 'Enhetsnamn',
            'organisation': 'Organisationsnamn',
        }

        data = self.parse_mappings(data_mappings, el)

        return data

    def parse_relation(self, el):
        return {
            'typ': el.get('AnnanTyp') if el.get('Typ') == 'Egen relationsdefinition' else el.get('Typ'),
            'referens': el.text
        }

    def parse_extra_id(self, el):
        if el.text is None:
            return None
        return {
            'typ': el.get('ExtraIDTyp'),
            'id': el.text
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

        for k, v in value_map.items():
            try:
                initiator_obj[k] = el.xpath(
                    "*/*[local-name()='Egenskap' and @Namn='%s']" % v
                )[0].xpath("*[local-name()='Varde']")[0].text
            except IndexError:
                pass

        return initiator_obj

    def parse_restriction(self, el):
        data_mappings = {
            'beskrivning': 'ForklarandeText',
            'lagrum': 'Lagrum',
            'upphor': 'RestriktionsDatum',
        }
        data = self.parse_mappings(data_mappings, el)

        typ = el.xpath("./@*[local-name()='Typ']")[0]
        try:
            annan_typ = el.xpath("./@*[local-name()='AnnanTyp']")[0]
        except IndexError:
            pass
        else:
            typ = annan_typ

        data['typ'] = str(typ)
        return data

    def parse_gallring(self, el):
        data_mappings = {
            'frist': 'GallringsFrist',
            'forklaring': 'GallringsForklaring',
            'period_slut': 'GallringsPeriodSlut',
        }
        data = self.parse_mappings(data_mappings, el)
        data['gallras'] = el.get('Gallras') == 'true'
        return data

    def parse_egenskaper(self, el):
        data_mappings = {
            'varde': 'Varde',
        }
        data = self.parse_mappings(data_mappings, el)
        data['namn'] = el.get('Namn')
        data['datatyp'] = el.get('DataTyp')
        data['format'] = el.get('Format')
        data['egenskaper'] = [self.parse_egenskaper(e) for e in
                              el.xpath('*[local-name()="Egenskaper"]/*[local-name()="Egenskap"]')]
        return data

    def parse_eget_element(self, el):
        data_mappings = {
            'varde': 'Varde',
        }
        data = self.parse_mappings(data_mappings, el)
        data['namn'] = el.get('Namn')
        if data['namn'] is not None:
            data['namn'] = remove_prefix(remove_prefix(data['namn'], "Dokument/"), "Ärende/")
        data['datatyp'] = el.get('DataTyp')
        data['format'] = el.get('Format')
        data['element'] = [self.parse_eget_element(e) for e in el.xpath('*[local-name()="EgetElement"]')]
        data['egenskaper'] = [self.parse_egenskaper(e) for e in
                              el.xpath('*[local-name()="Egenskaper"]/*[local-name()="Egenskap"]')]
        return data

    def parse_egna_element(self, el):
        data_mappings = {
            'beskrivning': 'EgnaElementBeskrivning',
        }
        data = self.parse_mappings(data_mappings, el)
        data['element'] = [self.parse_eget_element(e) for e in el.xpath('*[local-name()="EgetElement"]')]
        return data

    def parse_act(self, act, errand, ip):
        data_mappings = {
            'name': ['Rubrik', 'ArkivobjektID'],
            'status': 'StatusHandling',
            'handlingstyp': 'Handlingstyp',
            'klassreferens': 'KlassReferens',
            'arkivobjekt_id': 'ArkivobjektID',
        }

        data = self.parse_mappings(data_mappings, act)

        data['avsandare'] = []
        for avsandare in act.xpath("*[local-name()='Avsandare']"):
            data['avsandare'].append(self.parse_person(avsandare))

        data['mottagare'] = []
        for mottagare in act.xpath("*[local-name()='Mottagare']"):
            data['mottagare'].append(self.parse_person(mottagare))

        data['agenter'] = []
        for agent in act.xpath("*[local-name()='Agent']"):
            data['agenter'].append(self.parse_agent(agent))

        data['restriktioner'] = []
        for restriktion in act.xpath("*[local-name()='Restriktion']"):
            data['restriktioner'].append(self.parse_restriction(restriktion))

        data['relationer'] = []
        for relation in act.xpath("*[local-name()='HandlingRelation']"):
            data['relationer'].append(self.parse_relation(relation))

        data['extra_ids'] = []
        for extra_id in act.xpath("*[local-name()='ExtraID']"):
            parsed = self.parse_extra_id(extra_id)
            if parsed is not None:
                data['extra_ids'].append(parsed)

        try:
            data['gallring'] = self.parse_gallring(act.xpath("*[local-name()='Gallring']")[0])
        except IndexError:
            pass

        data['egna_element'] = []
        for egna_element in act.xpath("*[local-name()='EgnaElement']"):
            data['egna_element'].append(self.parse_egna_element(egna_element))

        date_mappings = {
            'dispatch_date': 'Expedierad',
            'arrival_date': 'Inkommen',
            'last_usage_date': 'SistaAnvandandetidpunkt',
            'create_date': 'Skapad',
            'preparation_date': 'Upprattad',
        }
        dates = self.parse_mappings(date_mappings, act)

        reference_code = act.xpath("*[local-name()='ArkivobjektID']")[0].text
        data['unit_ids'] = {'id': reference_code}

        data.update(dates)

        name = data.pop('name')
        tag = Tag.objects.create(information_package=ip, task=self.task)
        tag_version_type, _ = TagVersionType.objects.get_or_create(name='Handling')
        tag_version = TagVersion.objects.create(
            tag=tag,
            elastic_index='component',
            name=name,
            type=tag_version_type,
            reference_code=reference_code,
            custom_fields=data,
        )

        return tag_version

    def parse_mappings(self, mappings, el):
        data = {}
        for k, v in mappings.items():
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

    def parse_acts(self, ip, rootdir, errand, acts_root, parent, archive):
        for act_el in acts_root.xpath("*[local-name()='ArkivobjektHandling']"):
            tag_version = self.parse_act(act_el, errand, ip)
            act = Component.from_obj(tag_version, archive)

            tag_repr = TagStructure.objects.create(
                tag=tag_version.tag,
                parent=parent,
                structure=parent.structure,
                tree_id=parent.tree_id,
                lft=0,
                rght=0,
                level=0
            )

            for doc_el in act_el.xpath("*[local-name()='Bilaga']"):
                yield self.parse_document(ip, rootdir, doc_el, act, tag_repr, archive)

            yield tag_version.tag, tag_version, tag_repr, act.to_dict(include_meta=True)

    def parse_errand(self, errand, archive, ip, structure):
        unit_reference_code = errand.xpath("*[local-name()='KlassReferens']")[0].text
        try:
            structure_unit = StructureUnit.objects.get(structure=structure, reference_code=unit_reference_code)
        except StructureUnit.DoesNotExist:
            logger.exception('Structure unit {} not found in {}'.format(unit_reference_code, structure))
            raise

        data_mappings = {
            'name': ['Arendemening', 'Rubrik', 'ArkivobjektID'],
            'status': 'StatusArande',
            'arendetyp': 'ArendeTyp',
            'klassreferens': 'KlassReferens',
            'arkivobjekt_id': 'ArkivobjektID',
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

        data['egna_element'] = []
        for egna_element in errand.xpath("*[local-name()='EgnaElement']"):
            data['egna_element'].append(self.parse_egna_element(egna_element))

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

        reference_code = errand.xpath("*[local-name()='ArkivobjektID']")[0].text
        data['unit_ids'] = {'id': reference_code}

        name = data.pop('name')
        tag = Tag.objects.create(information_package=ip, task=self.task)
        tag_version_type, _ = TagVersionType.objects.get_or_create(name='Ärende')
        tag_version = TagVersion.objects.create(
            tag=tag,
            elastic_index='component',
            name=name,
            type=tag_version_type,
            reference_code=reference_code,
            custom_fields=data,
        )
        return tag_version, structure_unit

    def get_tag_structure(self, tag_version_id):
        return TagStructure.objects.filter(tag__versions__pk=tag_version_id).latest()

    def parse_errands(self, ip, rootdir, archive, errands_root):
        archive_structure = archive.get_active_structure()
        structure = archive_structure.structure
        for errand in self.get_arkiv_objekt_arenden(errands_root):
            tag_version, structure_unit = self.parse_errand(errand, archive, ip, structure)
            tag_repr = TagStructure.objects.create(
                tag=tag_version.tag,
                structure_unit=structure_unit,
                structure=structure,
                parent=archive_structure,
                tree_id=archive_structure.tree_id,
                lft=0,
                rght=0,
                level=0,
            )

            component = Component.from_obj(tag_version, archive)

            acts_root = self.get_acts_root(errand)
            if len(acts_root):
                for act in self.parse_acts(ip, rootdir, component, acts_root[0], tag_repr, archive):
                    yield act

            yield tag_version.tag, tag_version, tag_repr, component.to_dict(include_meta=True)

    def import_content(self, path, rootdir=None, ip=None, **extra_paths):
        if not rootdir:
            rootdir = os.path.dirname(path)

        self.indexed_files = []

        archive = self.get_archive(path)
        if not archive:
            archive = getattr(ip, 'tag', None)
            if not archive:
                raise ValueError('No archive found')
        else:
            archive = archive.tag.current_version

        logger.debug("Deleting task tags already in database...")
        Tag.objects.filter(task=self.task).delete()

        self.cleanup_elasticsearch(self.task)

        with transaction.atomic():
            with TagStructure.objects.delay_mptt_updates():
                tags, tag_versions, tag_structures, components = self.parse_eard(path, ip, rootdir, archive)

            self.task.update_progress(50)

        total = None
        if self.task is not None:
            total = TagVersion.objects.filter(tag__task=self.task).count()

        for _, count in self.save_to_elasticsearch(components):
            if self.task is not None:
                partial_progress = ((count / total) / 4) * 100
                self.task.update_progress(75 + partial_progress)

        self.task.update_progress(100)

        return self.indexed_files

    def parse_eard(self, xmlfile, ip, rootdir, archive):
        logger.debug("Parsing XML elements...")

        tree = etree.parse(xmlfile, self.xmlparser)
        root = tree.getroot()
        errands_root = self.get_errands_root(root)
        return zip(*self.parse_errands(ip, rootdir, archive, errands_root[0]))

    def save_to_database(self, tags, tag_versions, tag_structures, archive):
        logger.debug("Saving to Database...")
        with transaction.atomic():
            logger.debug("Rebuilding tree...")
            TagStructure.objects.partial_rebuild(archive.get_active_structure().tree_id)

        self.update_current_tag_versions()
