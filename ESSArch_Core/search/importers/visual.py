# -*- coding: utf-8 -*-

import errno
import logging
import os

from countries_plus.models import Country
from django.db import transaction
from django.db.models import OuterRef, Subquery, F, Q
from django.utils import dateparse, timezone
from elasticsearch_dsl.connections import get_connection
from elasticsearch_dsl import Search
from elasticsearch import helpers as es_helpers
from languages_plus.models import Language
from lxml import etree

from ESSArch_Core.search.importers.base import BaseImporter
from ESSArch_Core.tags.documents import Archive, Component, File
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
    AgentType,
    MainAgentType,
    RefCode,
    StructureUnit,
    Tag,
    TagStructure,
    TagVersion,
    Topography,
)

logger = logging.getLogger('essarch.search.importers.VisualImporter')
#es = get_connection()


AGENT_IDENTIFIER_TYPE = 'Visual arkivbildarnummer'
AGENT_NAME_TYPE = 'auktoriserad'
COUNTRY_CODE = 'SE'
REPO_CODE = 'SVK'  # TODO: just a dummy


class VisualImporter(BaseImporter):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.identifier_type, _ = AgentIdentifierType.objects.get_or_create(name=AGENT_IDENTIFIER_TYPE)
        self.agent_name_type, _ = AgentNameType.objects.get_or_create(name=AGENT_NAME_TYPE)
        self.ref_code, _ = RefCode.objects.get_or_create(
            country=Country.objects.get(iso=COUNTRY_CODE),
            repository_code=REPO_CODE,
        )

    def parse_arkivbildare(self, xmlpath, root):
        for arkivbildare in root.xpath("*[local-name()='arkivbildare']"):
            main_agent_type, _ = MainAgentType.objects.get_or_create(
                name=arkivbildare.xpath("*[local-name()='verksamtyp']/*[local-name()='typkod']")[0].text,
            )

            agent_type = AgentType.objects.create(  # TODO: get_or_create?
                cpf=arkivbildare.get('ipstyp'),
                main_type=main_agent_type,
            )

            agent = Agent.objects.create(
                type=agent_type,
                ref_code=self.ref_code,
                level_of_detail=Agent.PARTIAL,
                record_status=Agent.DRAFT,
                script=Agent.LATIN,
                language=Language.objects.get(iso_639_1='sv'),
                create_date=timezone.now(),  # TODO: change model to allow null?
                start_date=arkivbildare.get('verksamf'),
                end_date=arkivbildare.get('verksamt'),
            )

            AgentName.objects.create(
                agent=agent,
                main=arkivbildare.xpath("*[local-name()='arkivbildarnamn']")[0].text,
                type=self.agent_name_type,
            )

            tidnamn = arkivbildare.xpath("*[local-name()='tidnamn']")[0]
            if tidnamn.text:
                note_type_admin_anmerkning, _ = AgentNoteType.objects.get_or_create(
                    name='administrativ anmärkning'
                )
                AgentNote.objects.create(
                    agent=agent,
                    type=note_type_admin_anmerkning,
                    text=tidnamn.text,
                    create_date=timezone.now(),  # TODO: change model to allow null?
                )

            historik = arkivbildare.xpath("*[local-name()='historik']")
            if len(historik) and historik[0].text:
                historik = historik[0]

                note_type_historik, _ = AgentNoteType.objects.get_or_create(
                    name='historik',
                )
                AgentNote.objects.create(
                    agent=agent,
                    type=note_type_historik,
                    text=historik.text,
                    create_date=timezone.now(),  # TODO: change model to allow null?
                    revise_date=dateparse.parse_datetime(historik.get('andraddat'))
                )

            AgentIdentifier.objects.create(
                agent=agent,
                identifier=arkivbildare.get('arkivbildarnr'),
                type=self.identifier_type,
            )

            ort = arkivbildare.xpath("*[local-name()='ort']")[0].text
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

            yield agent

        return

    def update_progress(self, progress):
        self.task.progress = (progress / 100) * 100
        self.task.save()

    def import_content(self, task, path, rootdir=None, ip=None):
        if not rootdir:
            rootdir = os.path.dirname(path)

        self.indexed_files = []
        self.task = task

        Agent.objects.all().delete()
        self.parse_xml(path)

    @transaction.atomic
    def parse_xml(self, xmlfile):
        logger.debug("Parsing XML elements...")

        tree = etree.parse(xmlfile, self.xmlparser)
        root = tree.getroot()
        self.parse_arkivbildare(xmlfile, root)
