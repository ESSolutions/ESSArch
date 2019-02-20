# -*- coding: utf-8 -*-

from datetime import datetime
import logging
import uuid

import pytz
from countries_plus.models import Country
from django.core.cache import cache
from django.db import transaction
from django.db.models import OuterRef, Subquery, F
from django.utils import dateparse, timezone
from elasticsearch_dsl.connections import get_connection
from elasticsearch_dsl import Search
from elasticsearch import helpers as es_helpers
from languages_plus.models import Language
from lxml import etree

from ESSArch_Core.search.importers.base import BaseImporter
from ESSArch_Core.tags.documents import Archive, Component
from ESSArch_Core.tags.models import (
    Agent,
    AgentIdentifier,
    AgentIdentifierType,
    AgentName,
    AgentNameType,
    AgentNote,
    AgentNoteType,
    AgentPlace,
    AgentPlaceType,
    AgentTagLink,
    AgentTagLinkRelationType,
    AgentType,
    MainAgentType,
    RefCode,
    Structure,
    StructureUnit,
    Tag,
    TagStructure,
    TagVersion,
    Topography,
)

logger = logging.getLogger('essarch.search.importers.VisualImporter')
es = get_connection()


class VisualImporter(BaseImporter):
    NSMAP = {'va': 'http://www.visualarkiv.se/vaxml/v6.1'}

    ARKIV_XPATH = etree.XPath("va:arkiv", namespaces=NSMAP)
    SERIE_XPATH = etree.XPath("va:serier/va:serie", namespaces=NSMAP)
    VOLYM_XPATH = etree.XPath("va:volymer/va:volym", namespaces=NSMAP)

    AGENT_IDENTIFIER_TYPE = 'Visual arkivbildarnummer'
    AGENT_NAME_TYPE = 'auktoriserad'
    COUNTRY_CODE = 'SE'
    REPO_CODE = 'SVK'  # TODO: just a dummy

    AGENT_TAG_LINK_RELATION_TYPE, _ = AgentTagLinkRelationType.objects.get_or_create(name='creator')

    REF_CODE, _ = RefCode.objects.get_or_create(
        country=Country.objects.get(iso=COUNTRY_CODE),
        repository_code=REPO_CODE,
    )
    LANGUAGE = Language.objects.get(iso_639_1='sv')

    @classmethod
    def parse_agent_type(cls, arkivbildare):
        main_agent_type, _ = MainAgentType.objects.get_or_create(
            name=arkivbildare.xpath("va:verksamtyp/va:typkod", namespaces=cls.NSMAP)[0].text,
        )
        agent_type, _ = AgentType.objects.get_or_create(
            cpf=arkivbildare.get('ipstyp'),
            main_type=main_agent_type,
        )

        return agent_type

    @classmethod
    def parse_agent_names(cls, arkivbildare, agent):
        agent_name_type, _ = AgentNameType.objects.get_or_create(name=cls.AGENT_NAME_TYPE)

        name = AgentName.objects.create(
            agent=agent,
            main=arkivbildare.xpath("va:arkivbildarnamn", namespaces=cls.NSMAP)[0].text,
            type=agent_name_type,
        )
        return [name]

    @classmethod
    def parse_agent_notes(cls, arkivbildare, agent):
        notes = []

        tidnamn = arkivbildare.xpath("va:tidnamn", namespaces=cls.NSMAP)[0]
        if tidnamn.text:
            note_type_admin_anmerkning, _ = AgentNoteType.objects.get_or_create(
                name='administrativ anmärkning'
            )
            note = AgentNote.objects.create(
                agent=agent,
                type=note_type_admin_anmerkning,
                text=tidnamn.text,
                create_date=timezone.now(),  # TODO: change model to allow null?
            )
            notes.append(note)

        historik = arkivbildare.xpath("va:historik", namespaces=cls.NSMAP)
        if len(historik) and historik[0].text:
            historik = historik[0]
            historik_text = ''.join(historik.itertext()).replace('\n', '<br />')

            note_type_historik, _ = AgentNoteType.objects.get_or_create(
                name='historik',
            )
            note = AgentNote.objects.create(
                agent=agent,
                type=note_type_historik,
                text=historik_text,
                create_date=timezone.now(),  # TODO: change model to allow null?
                revise_date=dateparse.parse_datetime(historik.get('andraddat'))
            )
            notes.append(note)

        return notes

    @classmethod
    def parse_agent_identifiers(cls, arkivbildare, agent):
        identifier_type, _ = AgentIdentifierType.objects.get_or_create(name=cls.AGENT_IDENTIFIER_TYPE)

        identifier = AgentIdentifier.objects.create(
            agent=agent,
            identifier=arkivbildare.get('arkivbildarnr'),
            type=identifier_type,
        )
        return [identifier]

    @classmethod
    def parse_agent_places(cls, arkivbildare, agent):
        ort = arkivbildare.xpath("va:ort", namespaces=cls.NSMAP)[0].text
        if ort:
            topography, _ = Topography.objects.get_or_create(
                name=ort,
                type='Egen',
            )
            agent_place_type, _ = AgentPlaceType.objects.get_or_create(
                name='verksamhetsort'
            )
            AgentPlace.objects.create(
                agent=agent,
                topography=topography,
                type=agent_place_type,
            )

    @classmethod
    def parse_agent_start_date(cls, arkivbildare):
        start_year = arkivbildare.xpath('va:verksamf', namespaces=cls.NSMAP)[0].text
        start_date = None
        if start_year:
            start_date = datetime(
                year=int(start_year), month=1, day=1,
                tzinfo=pytz.UTC,
            )

        return start_date

    @classmethod
    def parse_agent_end_date(cls, arkivbildare):
        end_year = arkivbildare.xpath('va:verksamt', namespaces=cls.NSMAP)[0].text
        end_date = None
        if end_year:
            end_date = datetime(
                year=int(end_year), month=1, day=1,
                tzinfo=pytz.UTC,
            )

        return end_date

    @classmethod
    def parse_arkivbildare(cls, el, task=None):
        logger.debug("Parsing arkivbildare...")

        agent_type = cls.parse_agent_type(el)
        start_date = cls.parse_agent_start_date(el)
        end_date = cls.parse_agent_end_date(el)

        agent = Agent.objects.create(
            type=agent_type,
            ref_code=cls.REF_CODE,
            level_of_detail=Agent.PARTIAL,
            record_status=Agent.DRAFT,
            script=Agent.LATIN,
            language=cls.LANGUAGE,
            create_date=timezone.now(),  # TODO: change model to allow null?
            start_date=start_date,
            end_date=end_date,
            task=task,
        )

        cls.parse_agent_names(el, agent)
        cls.parse_agent_notes(el, agent)
        cls.parse_agent_identifiers(el, agent)
        cls.parse_agent_places(el, agent)

        logger.info("Parsed arkivbildare")

        return agent

    @classmethod
    def save_tags(cls, tags, tag_versions, tag_structures):
        logger.debug("Saving tags...")

        Tag.objects.bulk_create(tags, batch_size=100)
        TagVersion.objects.bulk_create(tag_versions, batch_size=100)
        with transaction.atomic():
            with TagStructure.objects.disable_mptt_updates():
                TagStructure.objects.bulk_create(tag_structures, batch_size=100)

        logger.info("Tags saved")

    @classmethod
    def update_current_tag_versions(cls, task):
        logger.debug("Update current tag versions...")

        versions = TagVersion.objects.filter(tag=OuterRef('pk'))
        Tag.objects.filter(
            task=task, current_version__isnull=True
        ).annotate(
            version=Subquery(versions.values('pk')[:1])
        ).update(
            current_version_id=F('version')
        )

        logger.info("Updated current tag versions")

    @classmethod
    def create_arkiv(cls, arkivbildare, agent=None, task=None, ip=None):
        for arkiv_el in cls.get_arkiv(arkivbildare):
            arkiv_doc, arkiv_tag, arkiv_version, arkiv_structure, arkiv_link = cls.parse_arkiv(
                arkiv_el, agent=agent, task=task, ip=ip
            )
            yield arkiv_doc.to_dict(include_meta=True), arkiv_tag, arkiv_version, arkiv_structure, arkiv_link

            for serie_el in cls.get_serier(arkiv_el):
                structure_unit = cls.parse_serie(
                    serie_el, arkiv_structure.structure, agent=agent, task=task, ip=ip,
                )

                for volym_el in cls.get_volymer(serie_el):
                    volym_doc, volym_tag, volym_version, volym_structure = cls.parse_volym(
                        volym_el, arkiv_version, arkiv_structure, structure_unit, agent=agent, task=task, ip=ip
                    )

                    volym_doc.archive = arkiv_version.pk
                    yield volym_doc.to_dict(include_meta=True), volym_tag, volym_version, volym_structure, None

    @staticmethod
    def get_arkiv(arkivbildare):
        return VisualImporter.ARKIV_XPATH(arkivbildare)

    @staticmethod
    def get_serier(arkiv):
        return VisualImporter.SERIE_XPATH(arkiv)

    @staticmethod
    def get_volymer(serie):
        return VisualImporter.VOLYM_XPATH(serie)

    @classmethod
    def parse_arkiv(cls, el, agent=None, task=None, ip=None):
        logger.debug("Parsing arkiv...")
        name = el.xpath("va:arkivnamn", namespaces=cls.NSMAP)[0].text
        tag_type = 'Arkiv'

        start_year = el.xpath("va:tidarkivf", namespaces=cls.NSMAP)[0].text
        start_date = None
        if start_year is not None:
            start_date = datetime(
                year=int(start_year), month=1, day=1,
                tzinfo=pytz.UTC,
            )

        end_year = el.xpath("va:tidarkivt", namespaces=cls.NSMAP)[0].text
        end_date = None
        if end_year is not None:
            end_date = datetime(
                year=int(end_year), month=1, day=1,
                tzinfo=pytz.UTC,
            )

        structure, _ = Structure.objects.get_or_create(  # TODO: get or create?
            name="Arkivförteckning för {}".format(name),
            version='1.0',
        )

        id = uuid.uuid4()
        doc = Archive(
            _id=id,
            current_version=True,
            name=name,
            type=tag_type,
            task_id=task.pk,
        )

        tag = Tag(information_package=ip, task=task)
        tag_version = TagVersion(
            pk=id,
            tag=tag,
            elastic_index='archive',
            type=tag_type,
            name=name,
            start_date=start_date,
            end_date=end_date,
        )
        tree_id = TagStructure.objects._get_next_tree_id()
        tag_structure = TagStructure(
            tag=tag,
            structure=structure,
            tree_id=tree_id,
            lft=0,
            rght=0,
            level=0
        )

        agent_tag_link = AgentTagLink(
            agent=agent,
            tag_id=tag_version.id,
            type=cls.AGENT_TAG_LINK_RELATION_TYPE,
        )
        logger.info("Parsed arkiv")
        return doc, tag, tag_version, tag_structure, agent_tag_link

    @classmethod
    def parse_serie(cls, el, structure, agent=None, task=None, ip=None):
        logger.debug("Parsing serie...")
        name = el.xpath("va:serierubrik", namespaces=cls.NSMAP)[0].text
        tag_type = el.get('level')
        reference_code = el.get("signum")

        parent_unit_id = None
        parent_reference_code = reference_code

        cache_key_prefix = str(structure.pk)

        while len(parent_reference_code) > 1:
            parent_reference_code = parent_reference_code.rsplit(maxsplit=1)[0]
            cache_key = '{}{}'.format(cache_key_prefix, parent_reference_code)
            parent_unit_id = cache.get(cache_key)

            if parent_unit_id is not None:
                break

        unit = StructureUnit.objects.create(
            structure=structure,
            name=name,
            parent_id=parent_unit_id,
            type=tag_type,
            reference_code=reference_code,
        )
        cache.set('{}{}'.format(cache_key_prefix, reference_code), str(unit.pk), 30)

        # TODO: store in new index in elasticsearch?

        logger.info("Parsed serie")
        return unit

    @classmethod
    def parse_volym(cls, el, archive_version, parent_tag_structure, structure_unit, agent=None, task=None, ip=None):
        logger.debug("Parsing volym...")
        ref_code = el.xpath("va:volnr", namespaces=cls.NSMAP)[0].text
        name = el.xpath("va:utseende", namespaces=cls.NSMAP)[0].text
        tag_type = "Volym"

        id = uuid.uuid4()
        doc = Component(
            _id=id,
            archive=str(archive_version.pk),
            structure_unit=str(structure_unit.pk),
            current_version=True,
            task_id=task.pk,
            name=name,
            reference_code=ref_code,
            type=tag_type,
        )

        tag = Tag(information_package=ip, task=task)
        tag_version = TagVersion(
            pk=id,
            tag=tag,
            elastic_index='component',
            reference_code=ref_code,
            name=name,
            type=tag_type,
        )
        tag_structure = TagStructure(
            tag=tag,
            structure_unit=structure_unit,
            structure=parent_tag_structure.structure,
            parent=parent_tag_structure,
            tree_id=parent_tag_structure.tree_id,
            lft=0,
            rght=0,
            level=0
        )

        logger.info("Parsed volym")
        return doc, tag, tag_version, tag_structure

    def import_content(self, task, path, rootdir=None, ip=None):
        self.indexed_files = []
        self.task = task
        self.ip = ip

        logger.debug("Importing data from {}...".format(path))
        self.cleanup(task)
        self.parse_xml(path)
        logger.info("Data imported from {}".format(path))

    @staticmethod
    def cleanup(task):
        logger.debug("Deleting task agents already in database...")
        Agent.objects.filter(task=task).delete()
        logger.info("Deleted task agents already in database...")

        # TODO: Delete structures (förteckningsplaner) connected to tags?
        Structure.objects.all().delete()

        logger.debug("Deleting task tags already in database...")
        Tag.objects.filter(task=task).delete()
        logger.info("Deleted task tags already in database...")

        # Delete from elastic
        logger.debug("Deleting task tags already in Elasticsearch...")
        indices_to_delete = [doc._index._name for doc in [Archive, Component]]
        Search(using=es, index=indices_to_delete).query('term', task_id=str(task.pk)).delete()
        logger.info("Deleted task tags already in Elasticsearch...")

    @transaction.atomic
    def parse_xml(self, xmlfile):
        logger.debug("Parsing XML elements...")

        tree = etree.parse(xmlfile, self.xmlparser)
        root = tree.getroot()

        all_docs = []
        for arkivbildare in root.xpath("va:arkivbildare", namespaces=self.NSMAP):
            agent = self.parse_arkivbildare(arkivbildare, task=self.task)

            docs, tags, tag_versions, tag_structures, agent_tag_links = zip(
                *self.create_arkiv(
                    arkivbildare, agent=agent, task=self.task, ip=self.ip
                )
            )
            all_docs.extend(all_docs)

            self.save_tags(tags, tag_versions, tag_structures)
            self.update_current_tag_versions(self.task)

            agent_tag_links = [x for x in agent_tag_links if x is not None]
            AgentTagLink.objects.bulk_create(agent_tag_links, batch_size=100)

        logger.info("XML elements parsed")

        self.save_to_elasticsearch(all_docs, self.task)

        logger.debug("Rebuilding trees...")
        TagStructure.objects.rebuild()
        logger.info("Trees rebuilt")

    @classmethod
    def save_to_elasticsearch(cls, components, task=None):
        logger.debug("Saving to Elasticsearch...")
        count = 0
        total = None

        if task is not None:
            total = TagVersion.objects.filter(tag__task=task).count()

        for ok, result in es_helpers.streaming_bulk(es, components):
            action, result = result.popitem()
            doc_id = result['_id']
            doc = '/%s/%s' % (result['_index'], doc_id)

            if not ok:
                logger.error('Failed to %s document %s: %r' % (action, doc, result))
            else:
                logger.debug('Saved document %s: %r' % (doc, result))
                if task is not None:
                    count += 1
                    partial_progress = ((count / total) / 4) * 100
                    task.update_progress(75 + partial_progress)

        logger.info("Documents saved to Elasticsearch")
