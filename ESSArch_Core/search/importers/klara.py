# -*- coding: utf-8 -*-

import hashlib
import html
import logging
import re
import uuid
from datetime import datetime
from itertools import chain

import pytz
from countries_plus.models import Country
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from languages_plus.models import Language
from lxml import etree

from ESSArch_Core.agents.documents import AgentDocument
from ESSArch_Core.agents.models import (
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
    Topography,
)
from ESSArch_Core.search.importers.base import BaseImporter
from ESSArch_Core.tags.documents import (
    Archive,
    Component,
    StructureUnitDocument,
)
from ESSArch_Core.tags.models import (
    MediumType,
    NodeIdentifier,
    NodeIdentifierType,
    NodeNote,
    NodeNoteType,
    NodeRelationType,
    RuleConventionType,
    Structure,
    StructureType,
    StructureUnit,
    StructureUnitType,
    Tag,
    TagStructure,
    TagVersion,
    TagVersionRelation,
    TagVersionType,
)

logger = logging.getLogger('essarch.search.importers.KlaraImporter')


class KlaraImporter(BaseImporter):
    VOLUME_RELATION_REGEX = re.compile(r'[ABCDEFGHJKLÖ]+\s*[A-Za-zÅÖÖåäö0-9]+\s*\:\s*[0-9]+')

    SERIE_XPATH = etree.XPath("ObjectParts/Series/Archive.Series/Series")

    AGENT_IDENTIFIER_TYPE = 'Klara'
    AGENT_NAME_TYPE = 'auktoriserad'
    AGENT_ALT_NAME_TYPE = 'alternativt'
    AGENT_TAG_LINK_RELATION_TYPE_NAME = 'creator'
    COUNTRY_CODE = 'SE'
    LANGUAGE_CODE = 'sv'
    NODE_IDENTIFIER_TYPE_KLARA_NAME = 'Klara-id'
    NODE_NOTE_TYPE_HISTORIK_NAME = 'Historik'
    REPO_CODE = 'C020'  # TODO: just a dummy
    VOLUME_RELATION_TYPE_NAME = 'associative'

    _ref_code = None
    _language = None
    _name_type = None
    _alt_name_type = None
    _tag_link_relation_type = None
    _note_type_anmarkning = None
    _note_type_historik = None
    _medium_type_logisk = None
    _node_identifier_type_klara = None
    _volume_relation_type = None
    _node_note_type_historik = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.STRUCTURE_TYPE, _ = StructureType.objects.get_or_create(name='Förteckning')
        self.ARCHIVE_TYPE, _ = TagVersionType.objects.get_or_create(name='Arkiv', archive_type=True)
        self.SERIE_TYPE, _ = StructureUnitType.objects.get_or_create(name='Serie', structure_type=self.STRUCTURE_TYPE)
        self.VOLUME_TYPE, _ = TagVersionType.objects.get_or_create(name='Volym', archive_type=False)

    @property
    def ref_code(self):
        if self._ref_code is None:
            self._ref_code, _ = RefCode.objects.get_or_create(
                country=Country.objects.get(iso=self.COUNTRY_CODE),
                repository_code=self.REPO_CODE,
            )
        return self._ref_code

    @property
    def language(self):
        if self._language is None:
            self._language = Language.objects.get(iso_639_1=self.LANGUAGE_CODE)
        return self._language

    @property
    def name_type(self):
        if self._name_type is None:
            self._name_type, _ = AgentNameType.objects.get_or_create(name=self.AGENT_NAME_TYPE)
        return self._name_type

    @property
    def alt_name_type(self):
        if self._alt_name_type is None:
            self._alt_name_type, _ = AgentNameType.objects.get_or_create(name=self.AGENT_ALT_NAME_TYPE)
        return self._alt_name_type

    @property
    def tag_link_relation_type(self):
        if self._tag_link_relation_type is None:
            self._tag_link_relation_type, _ = AgentTagLinkRelationType.objects.get_or_create(
                name=self.AGENT_TAG_LINK_RELATION_TYPE_NAME
            )
        return self._tag_link_relation_type

    @property
    def note_type_anmarkning(self):
        if self._note_type_anmarkning is None:
            self._note_type_anmarkning, _ = AgentNoteType.objects.get_or_create(name='administrativ anmärkning')
        return self._note_type_anmarkning

    @property
    def note_type_historik(self):
        if self._note_type_historik is None:
            self._note_type_historik, _ = AgentNoteType.objects.get_or_create(name='historik')
        return self._note_type_historik

    @property
    def medium_type_logisk(self):
        if self._medium_type_logisk is None:
            self._medium_type_logisk, _ = MediumType.objects.get_or_create(name='Logisk')
        return self._medium_type_logisk

    @property
    def node_identifier_type_klara(self):
        if self._node_identifier_type_klara is None:
            self._node_identifier_type_klara, _ = NodeIdentifierType.objects.get_or_create(
                name=self.NODE_IDENTIFIER_TYPE_KLARA_NAME
            )
        return self._node_identifier_type_klara

    @property
    def node_note_type_historik(self):
        if self._node_note_type_historik is None:
            self._node_note_type_historik, _ = NodeNoteType.objects.get_or_create(
                name=self.NODE_NOTE_TYPE_HISTORIK_NAME
            )
        return self._node_note_type_historik

    @property
    def volume_relation_type(self):
        if self._volume_relation_type is None:
            self._volume_relation_type, _ = NodeRelationType.objects.get_or_create(
                name=self.VOLUME_RELATION_TYPE_NAME,
            )
        return self._volume_relation_type

    @staticmethod
    def _parse_timestamp(ts):
        date_format = "%Y-%m-%d %H:%M:%S:%f"
        tPart, tzPart = ts.rsplit(' ', 1)
        tzPart = tzPart.replace('CEST', 'CET')

        dt = datetime.strptime(tPart, date_format)
        tz = pytz.timezone(tzPart)
        return tz.localize(dt)

    @staticmethod
    def _parse_year_string(year_str, end=False):
        """
        Parses a string containing only the year, e.g.: "2019"

        Args:
            year_str (str): The year
            end (bool): Returns the end of the year if true, else the start

        Returns:
            A datetime object at the very start or very end of the given year
        """

        d = datetime.strptime(year_str, '%Y')

        if end:
            d = d.replace(month=12, day=31)

        return d

    @staticmethod
    def get_series(archive):
        return KlaraImporter.SERIE_XPATH(archive)

    @classmethod
    def parse_agent_type(cls, arkivbildare):
        main_agent_type, _ = MainAgentType.objects.get_or_create(
            name=arkivbildare.xpath("ObjectParts/General/ArchiveOrig.Parent.Name")[0].text,
        )

        category_name = arkivbildare.xpath("ObjectParts/General/ArchOrigCategory.Name")[0].text
        if category_name == 'Person (släkt)':
            cpf = AgentType.PERSON
        else:
            cpf = AgentType.CORPORATE_BODY

        agent_type, _ = AgentType.objects.get_or_create(
            cpf=cpf,
            main_type=main_agent_type,
            sub_type=category_name,
        )

        return agent_type

    @classmethod
    def _parse_agent_alternative_names(cls, arkivbildare, agent, name_type):
        for name_el in arkivbildare.xpath("ObjectParts/AltNames/ArchiveOrig.AltNames/ArchOrigAltName"):
            alt_name = AgentName.objects.create(
                agent=agent,
                main=name_el.xpath("ArchOrigAltName.Name")[0].text,
                type=name_type,
                start_date=cls._parse_year_string(name_el.xpath("ArchOrigAltName.UsedFrom")[0].text),
                end_date=cls._parse_year_string(name_el.xpath("ArchOrigAltName.UsedTo")[0].text, end=True),
            )
            yield alt_name

    @classmethod
    def parse_agent_names(cls, arkivbildare, agent, name_type, alt_name_type):
        authorized_name = AgentName.objects.create(
            agent=agent,
            main=arkivbildare.xpath("ObjectParts/General/ArchiveOrig.Name")[0].text,
            type=name_type,
        )

        alt_names = list(cls._parse_agent_alternative_names(arkivbildare, agent, alt_name_type))
        return [authorized_name] + alt_names

    @classmethod
    def parse_agent_notes(cls, arkivbildare, agent, anmarkning_type, historik_type):
        notes = []

        create_date = cls.parse_agent_create_date(arkivbildare)
        created_by = cls.parse_agent_created_by(arkivbildare)

        created_text = (
            'Auktoritetsposten upprättades {date} i arkivredovisningssystemet Klara av användare {name}'.format(
                date=create_date,
                name=created_by,
            )
        )
        created_note = AgentNote.objects.create(
            agent=agent,
            type=anmarkning_type,
            text=created_text,
            create_date=timezone.now(),
        )
        notes.append(created_note)

        revise_date = cls.parse_agent_revise_date(arkivbildare)
        revised_by = cls.parse_agent_revised_by(arkivbildare)

        revised_text = (
            'Auktoritetsposten ändrades {date} i arkivredovisningssystemet Klara av användare {name}'.format(
                date=revise_date,
                name=revised_by,
            )
        )
        revised_note = AgentNote.objects.create(
            agent=agent,
            type=anmarkning_type,
            text=revised_text,
            create_date=timezone.now(),
        )
        notes.append(revised_note)

        historik = arkivbildare.xpath("ObjectParts/Notes/ArchiveOrig.Notes")
        if len(historik) and historik[0].text:
            historik = historik[0].text

            note = AgentNote.objects.create(
                agent=agent,
                type=historik_type,
                text=historik,
                create_date=cls.parse_agent_revise_date(arkivbildare),
                revise_date=cls.parse_agent_revise_date(arkivbildare),
            )
            notes.append(note)

        return notes

    @classmethod
    def parse_agent_identifiers(cls, arkivbildare, agent):
        identifier_type, _ = AgentIdentifierType.objects.get_or_create(name=cls.AGENT_IDENTIFIER_TYPE)
        identifier_text = arkivbildare.xpath("ObjectKey/ArchiveOrig.ArchiveOrigID")[0].text

        identifier = AgentIdentifier.objects.create(
            agent=agent,
            identifier='{}/{}'.format(cls.REPO_CODE, identifier_text),
            type=identifier_type,
        )
        return [identifier]

    @classmethod
    def parse_agent_topography(cls, arkivbildare):
        name = arkivbildare.xpath("ObjectParts/General/ArchiveOrig.TopographicName")[0].text

        if name is None:
            return None

        topography, _ = Topography.objects.get_or_create(
            name=name,
            type='Lokal term',
        )
        return topography

    @classmethod
    def parse_agent_places(cls, arkivbildare, agent):
        topography = cls.parse_agent_topography(arkivbildare)
        agent_place_type, _ = AgentPlaceType.objects.get_or_create(
            name='verksamhetsort'
        )
        AgentPlace.objects.create(
            agent=agent,
            topography=topography,
            type=agent_place_type,
        )

    @classmethod
    def parse_agent_level_of_detail(cls, arkivbildare):
        publish = arkivbildare.xpath('ObjectParts/General/ArchiveOrig.Publish')[0].text
        if publish == 'true':
            return Agent.FULL

        return Agent.PARTIAL

    @classmethod
    def parse_agent_record_status(cls, arkivbildare):
        publish = arkivbildare.xpath('ObjectParts/General/ArchiveOrig.Publish')[0].text
        if publish == 'true':
            return Agent.FINAL

        return Agent.DRAFT

    @classmethod
    def parse_agent_create_date(cls, arkivbildare):
        try:
            date_string = arkivbildare.xpath('ObjectParts/General/ArchiveOrig.CreatedWhen')[0].text
            if date_string is None:
                return cls.parse_agent_revise_date(arkivbildare)

            return cls._parse_timestamp(date_string)
        except IndexError:
            return cls.parse_agent_revise_date(arkivbildare)

    @classmethod
    def parse_agent_created_by(cls, arkivbildare):
        return arkivbildare.xpath('ObjectParts/General/ArchiveOrig.CreatedBy')[0].text

    @classmethod
    def parse_agent_revise_date(cls, arkivbildare):
        date_string = arkivbildare.xpath('ObjectParts/General/ArchiveOrig.ModifiedWhen')[0].text
        return cls._parse_timestamp(date_string)

    @classmethod
    def parse_agent_revised_by(cls, arkivbildare):
        return arkivbildare.xpath('ObjectParts/General/ArchiveOrig.ModifiedBy')[0].text

    @classmethod
    def parse_agent_start_date(cls, arkivbildare):
        start_year = arkivbildare.xpath('ObjectParts/General/ArchiveOrig.ExistFrom')[0].text
        if start_year:
            return cls._parse_year_string(start_year)

    @classmethod
    def parse_agent_end_date(cls, arkivbildare):
        end_year = arkivbildare.xpath('ObjectParts/General/ArchiveOrig.ExistTo')[0].text
        if end_year:
            return cls._parse_year_string(end_year, end=True)

    def parse_arkivbildare(self, el, task):
        logger.info("Parsing arkivbildare...")

        agent_type = self.parse_agent_type(el)

        level_of_detail = self.parse_agent_level_of_detail(el)
        record_status = self.parse_agent_record_status(el)

        create_date = self.parse_agent_create_date(el)
        revise_date = self.parse_agent_revise_date(el)

        start_date = self.parse_agent_start_date(el)
        end_date = self.parse_agent_end_date(el)

        agent = Agent.objects.create(
            type=agent_type,
            ref_code=self.ref_code,
            level_of_detail=level_of_detail,
            record_status=record_status,
            script=Agent.LATIN,
            language=self.language,
            create_date=create_date,
            revise_date=revise_date,
            start_date=start_date,
            end_date=end_date,
            task=task,
        )

        self.parse_agent_names(el, agent, self.name_type, self.alt_name_type)
        self.parse_agent_notes(el, agent, self.note_type_anmarkning, self.note_type_historik)
        self.parse_agent_identifiers(el, agent)
        self.parse_agent_places(el, agent)

        logger.info("Parsed arkivbildare: {}".format(agent.pk))

        return agent

    @classmethod
    def parse_archive_create_date(cls, el):
        create_date = el.xpath('ObjectParts/General/Archive.CreatedWhen')[0].text
        if create_date is None:
            return None

        return cls._parse_timestamp(create_date)

    @classmethod
    def parse_archive_revise_date(cls, el):
        revise_date = el.xpath('ObjectParts/General/Archive.ModifiedWhen')[0].text
        if revise_date is None:
            return None

        return cls._parse_timestamp(revise_date)

    @classmethod
    def parse_archive_start_date(cls, el):
        """
        Gets the start date of the archive

        Args:
            el (etree.ElementBase): The <Archive> element

        Returns:
            The start date of the archive as a datetime object
            if there is one, otherwise None
        """

        start_year = el.xpath('ObjectParts/General/Archive.DateBegin')[0].text
        if start_year:
            return cls._parse_year_string(start_year)

    @classmethod
    def parse_archive_end_date(cls, el):
        """
        Gets the end date of the archive

        Args:
            el (etree.ElementBase): The <Archive> element

        Returns:
            The end date of the archive as a datetime object
            if there is one, otherwise None
        """

        end_year = el.xpath('ObjectParts/General/Archive.DateEnd')[0].text
        if end_year:
            return cls._parse_year_string(end_year, end=True)

    def parse_archive(self, el, task=None, ip=None):
        name = el.xpath('ObjectParts/General/Archive.Name')[0].text
        orig_name = el.xpath('ObjectParts/General/ArchiveOrig.Name')[0].text
        create_date = self.parse_archive_create_date(el)
        revise_date = self.parse_archive_revise_date(el)
        tag_type = self.ARCHIVE_TYPE

        tag = Tag.objects.create(information_package=ip, task=task)

        archive_id = uuid.uuid4()
        tag_version = TagVersion.objects.create(
            pk=archive_id,
            tag=tag,
            reference_code=el.xpath('ObjectParts/General/Archive.RefCode')[0].text,
            type=tag_type,
            name=name,
            elastic_index='archive',
            create_date=create_date,
            revise_date=revise_date,
            import_date=timezone.now(),
            start_date=self.parse_archive_start_date(el),
            end_date=self.parse_archive_end_date(el),
        )

        inst_code = el.xpath("ObjectParts/General/ArchiveInst.InstCode")[0].text
        archive_klara_id = el.xpath("ObjectParts/General/Archive.ArchiveID")[0].text
        NodeIdentifier.objects.create(
            identifier="{}/{}".format(inst_code, archive_klara_id),
            tag_version=tag_version,
            type=self.node_identifier_type_klara,
        )

        history_note_text = el.xpath("ObjectParts/History/Archive.History")[0].text
        if history_note_text:
            NodeNote.objects.create(
                text=html.unescape(history_note_text),
                tag_version=tag_version,
                type=self.node_note_type_historik,
                create_date=timezone.now(),  # TODO: use something else to get the date?
                revise_date=timezone.now(),  # TODO: use something else to get the date?
            )

        rule_convention_type, _ = RuleConventionType.objects.get_or_create(
            name=el.xpath("ObjectParts/General/ArchiveType.Name")[0].text,
        )

        structure = Structure.objects.create(
            name="Arkivförteckning för {}".format(orig_name),
            type=self.STRUCTURE_TYPE,
            is_template=True,
            published=True,
            published_date=timezone.now(),
            version='1.0',
            create_date=create_date,
            rule_convention_type=rule_convention_type,
            task=task,
        )
        structure_instance, tag_structure = structure.create_template_instance(tag)

        for instance_unit in structure_instance.units.all():
            StructureUnitDocument.from_obj(instance_unit).save()

        agent_hash = self.build_agent_hash(
            el.xpath('ObjectParts/General/Archive.ArchiveOrigID')[0].text,
            orig_name,
        )
        agent_id = cache.get(agent_hash)

        AgentTagLink.objects.create(
            agent_id=agent_id,
            tag=tag_version,
            type=self.tag_link_relation_type,
        )

        doc = Archive.from_obj(tag_version).to_dict(include_meta=True)

        return doc, tag, tag_version, tag_structure, inst_code

    @staticmethod
    def build_agent_hash(archive_orig_id, archive_orig_name):
        m = hashlib.sha256()
        m.update(archive_orig_id.encode('utf-8'))
        m.update(archive_orig_name.encode('utf-8'))
        return m.digest()

    @staticmethod
    def build_archive_hash(archive_id, archive_name, agent_hash):
        m = hashlib.sha256()
        m.update(archive_id.encode('utf-8'))
        m.update(archive_name.encode('utf-8'))
        m.update(agent_hash)
        return m.digest()

    @staticmethod
    def build_series_hash(series_id, series_signum, series_title, archive_hash):
        m = hashlib.sha256()
        m.update(series_id.encode('utf-8'))
        m.update(series_signum.encode('utf-8'))
        m.update(series_title.encode('utf-8'))
        m.update(archive_hash)
        return m.digest()

    def parse_series(self, el, structure, inst_code, task):
        logger.debug("Parsing series...")
        name = el.xpath("Series.Title")[0].text
        tag_type = self.SERIE_TYPE
        reference_code = el.xpath("Series.Signum")[0].text

        parent_unit_id = None
        cache_key_prefix = str(structure.pk)

        if reference_code[-1].islower():
            parent_reference_code = reference_code

            while len(parent_reference_code) > 1:
                parent_reference_code = parent_reference_code[:-1]
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
            task=task,
        )

        series_id = el.xpath("Series.SeriesID")[0].text
        NodeIdentifier.objects.create(
            identifier="{}/{}".format(inst_code, series_id),
            structure_unit=unit,
            type=self.node_identifier_type_klara,
        )

        # save for building tree
        cache.set('{}{}'.format(cache_key_prefix, reference_code), str(unit.pk), 300)

        logger.debug("Parsed series: {}".format(unit.pk))
        return unit

    def parse_volume(self, el, medium_type_logisk, task, ip=None):
        logger.debug("Parsing volume...")
        tag_type = self.VOLUME_TYPE

        ref_code = el.xpath("Volume.VolumeCode")[0].text
        name = el.xpath("Volume.Title")[0].text or ""

        date = el.xpath("Volume.Date")[0].text
        start_date = self._parse_year_string(date[:4]) if date and len(date) >= 4 else None
        end_date = self._parse_year_string(date[-4:], end=True) if date and len(date) == 4 else None

        short_name = el.xpath("VolumeType.ShortName")[0].text
        if short_name == 'L':
            medium_type = medium_type_logisk
        else:
            medium_type = None

        volume_id = str(uuid.uuid4())

        agent_hash = self.build_agent_hash(
            el.xpath("ArchiveOrig.ArchiveOrigID")[0].text,
            el.xpath("ArchiveOrig.Name")[0].text,
        )
        agent_id = cache.get(agent_hash)

        archive_hash = self.build_archive_hash(
            el.xpath("Archive.ArchiveID")[0].text,
            el.xpath("Archive.Name")[0].text,
            agent_hash,
        )

        archive_tag_id = cache.get(archive_hash)
        archive_tag = Tag.objects.select_related(
            'current_version'
        ).prefetch_related(
            'structures'
        ).get(
            pk=archive_tag_id
        )

        series_hash = self.build_series_hash(
            el.xpath("Series.SeriesID")[0].text,
            el.xpath("Series.Signum")[0].text,
            el.xpath("Series.Title")[0].text,
            archive_hash,
        )
        unit_id = cache.get(series_hash)
        unit = StructureUnit.objects.get(pk=unit_id)

        tag = Tag.objects.create(information_package=ip, task=task)
        tag_version = TagVersion.objects.create(
            pk=volume_id,
            tag=tag,
            elastic_index='component',
            reference_code=ref_code,
            name=name,
            type=tag_type,
            create_date=None,
            import_date=timezone.now(),
            start_date=start_date,
            end_date=end_date,
            medium_type=medium_type,
        )

        AgentTagLink.objects.create(
            agent_id=agent_id,
            tag=tag_version,
            type=self.tag_link_relation_type,
        )

        related_id_match = self.VOLUME_RELATION_REGEX.search(name)
        if related_id_match:
            relation_cache_key = 'relation_{}'.format(volume_id)
            match_without_whitespace = re.sub(r'\s+', '', related_id_match.group(0))
            cache.set(relation_cache_key, match_without_whitespace, 300)

        TagStructure.objects.create(
            tag=tag,
            structure_unit=unit,
            structure=unit.structure,
            parent=archive_tag.get_active_structure()
        )

        doc = Component.from_obj(tag_version, archive=archive_tag.current_version)

        logger.debug("Parsed volume: {}".format(tag_version.pk))
        return doc.to_dict(include_meta=True), tag_version

    def import_content(self, agent_xml_path, rootdir=None, ip=None, **extra_paths):
        self.indexed_files = []
        self.ip = ip
        docs = []

        logger.info("Importing data from {}...".format(agent_xml_path))
        self.cleanup()
        docs += list(self.parse_agent_xml(agent_xml_path))
        logger.info("Data imported from {}".format(agent_xml_path))

        archive_xml_path = extra_paths.get('archive_xml')
        if archive_xml_path:
            logger.info("Importing archives and series from {}...".format(archive_xml_path))
            docs += list(self.parse_archive_xml(archive_xml_path))
            logger.info("Archive and series imported from {}".format(archive_xml_path))

            volume_xml_path = extra_paths.get('volume_xml')
            if volume_xml_path:
                logger.info("Importing volumes from {}...".format(volume_xml_path))
                volume_docs = list(self.parse_volume_xml(volume_xml_path))
                docs = chain(docs, volume_docs)
                logger.info("Volumes imported from {}".format(volume_xml_path))

                logger.info("Creating relations between volumes...")

                for tag_version in TagVersion.objects.filter(tag__task=self.task).iterator():
                    logger.debug("Getting related reference from cache...")
                    relation_cache_key = 'relation_{}'.format(str(tag_version.pk))
                    related_ref = cache.get(relation_cache_key)
                    if related_ref:
                        logger.debug("Related reference found in cache")
                        related_series_ref, related_volume_ref = related_ref.split(':')
                        # TODO replace this with something faster (and safer and more correct?)
                        try:
                            related_tag_version = TagVersion.objects.get(
                                tag__task=self.task,
                                reference_code=related_volume_ref,
                                tag__structures__structure_unit__reference_code=related_series_ref,
                            )
                        except TagVersion.DoesNotExist:
                            logger.exception(
                                'Related tag version with reference "{}" not found, skipping...'.format(related_ref)
                            )
                        else:
                            TagVersionRelation.objects.bulk_create([
                                TagVersionRelation(
                                    tag_version_a=tag_version,
                                    tag_version_b=related_tag_version,
                                    type=self.volume_relation_type,
                                ),
                                TagVersionRelation(
                                    tag_version_a=related_tag_version,
                                    tag_version_b=tag_version,
                                    type=self.volume_relation_type,
                                )
                            ])
                    else:
                        logger.debug("No related reference found in cache")

                logger.info("Relations created between volumes ")

            self.update_current_tag_versions()

        total = None
        if self.task is not None:
            docs = list(docs)
            total = len(docs)

        for _, count in self.save_to_elasticsearch(docs):
            if self.task is not None:
                partial_progress = ((count / total) / 4) * 100
                self.task.update_progress(75 + partial_progress)

    def cleanup(self):
        logger.info("Deleting task agents already in database...")
        Agent.objects.filter(task=self.task).delete()
        logger.info("Deleted task agents already in database")

        logger.info("Deleting task structure units already in database...")
        StructureUnit.objects.filter(task=self.task).delete()
        logger.info("Deleted task structure units already in database")

        logger.info("Deleting task structures already in database...")
        Structure.objects.filter(task=self.task).delete()
        logger.info("Deleted task structures already in database")

        logger.info("Deleting task tags already in database...")
        Tag.objects.filter(task=self.task).delete()
        logger.info("Deleted task tags already in database")

        self.cleanup_elasticsearch(self.task)

    @transaction.atomic
    def parse_agent_xml(self, xmlfile):
        logger.info("Parsing agent XML elements...")

        tree = etree.parse(xmlfile, self.xmlparser)
        root = tree.getroot()

        for arkivbildare in root.xpath("ArchiveOrig"):
            agent = self.parse_arkivbildare(arkivbildare, task=self.task)
            agent_hash = self.build_agent_hash(
                arkivbildare.xpath('ObjectParts/General/ArchiveOrig.ArchiveOrigID')[0].text,
                arkivbildare.xpath('ObjectParts/General/ArchiveOrig.Name')[0].text,
            )
            cache.set(agent_hash, agent.pk, 300)

            yield AgentDocument.from_obj(agent).to_dict(include_meta=True)

        logger.info("Agent XML elements parsed")

    @transaction.atomic
    def parse_archive_xml(self, xmlfile):
        logger.info("Parsing archive XML elements...")

        tree = etree.parse(xmlfile, self.xmlparser)
        root = tree.getroot()

        for archive_el in root.xpath("Archive"):
            archive_doc, archive_tag, archive_tag_version, archive_tag_structure, inst_code = self.parse_archive(
                archive_el, task=self.task, ip=self.ip
            )

            structure = archive_tag_structure.structure
            structure_template = structure.template

            agent_hash = self.build_agent_hash(
                archive_el.xpath("ObjectParts/General/Archive.ArchiveOrigID")[0].text,
                archive_el.xpath("ObjectParts/General/ArchiveOrig.Name")[0].text
            )

            archive_id = archive_el.xpath("ObjectParts/General/Archive.ArchiveID")[0].text
            archive_name = archive_el.xpath("ObjectParts/General/Archive.Name")[0].text

            archive_hash = self.build_archive_hash(
                archive_id,
                archive_name,
                agent_hash,
            )

            cache.set(archive_hash, archive_tag.pk, 300)

            for series_el in self.get_series(archive_el):
                series_template_structure_unit = self.parse_series(
                    series_el,
                    structure_template,
                    inst_code,
                    task=self.task,
                )
                unit = series_template_structure_unit.create_template_instance(structure)

                series_id = series_el.xpath("Series.SeriesID")[0].text
                series_signum = series_el.xpath("Series.Signum")[0].text
                series_title = series_el.xpath("Series.Title")[0].text

                series_hash = self.build_series_hash(
                    series_id,
                    series_signum,
                    series_title,
                    archive_hash,
                )

                cache.set(series_hash, unit.pk, 300)

                doc = StructureUnitDocument.from_obj(unit)
                yield doc.to_dict(include_meta=True)

            yield archive_doc

        logger.info("Archive XML elements parsed")

    @transaction.atomic
    def parse_volume_xml(self, xmlfile):
        logger.info("Parsing volume XML elements...")

        tree = etree.parse(xmlfile, self.xmlparser)
        root = tree.getroot()

        for volume_el in root.xpath("Volume"):
            volume_doc, volume_tag_versions = self.parse_volume(
                volume_el,
                self.medium_type_logisk,
                task=self.task,
                ip=self.ip,
            )

            yield volume_doc

        logger.info("Volume XML elements parsed")
