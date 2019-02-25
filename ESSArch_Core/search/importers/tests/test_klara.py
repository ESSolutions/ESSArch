import pytz

from datetime import datetime
from lxml import objectify

from django.test import TestCase
from django.utils import timezone

from ESSArch_Core.search.importers.klara import KlaraImporter
from ESSArch_Core.tags.models import Agent, AgentName, AgentType, MainAgentType


class ParseTimestampTests(TestCase):
    def test_parse_timestamp_cet(self):
        tz = pytz.timezone('CET')

        dt = KlaraImporter._parse_timestamp('1994-01-20 01:02:03:456 CET')
        self.assertEqual(dt, tz.localize(datetime(1994, 1, 20, 1, 2, 3, 456000)))

    def test_parse_timestamp_cest(self):
        tz = pytz.timezone('CET')

        # test winter
        dt = KlaraImporter._parse_timestamp('1994-01-20 01:02:03:456 CEST')
        self.assertEqual(dt, tz.localize(datetime(1994, 1, 20, 1, 2, 3, 456000)))

        # test summer
        dt = KlaraImporter._parse_timestamp('1994-07-20 01:02:03:456 CEST')
        self.assertEqual(dt, tz.localize(datetime(1994, 7, 20, 1, 2, 3, 456000)))


class ParseAgentTypeTests(TestCase):
    def test_parse_person(self):
        xml = '''
            <ArchiveOrig>
                <ObjectParts type="ValueMap">
                    <General type="ValueMap">
                        <ArchiveOrig.Parent.Name type="String">Nationell nivå</ArchiveOrig.Parent.Name>
                        <ArchOrigCategory.Name type="String">Person (släkt)</ArchOrigCategory.Name>
                    </General>
                </ObjectParts>
            </ArchiveOrig>
        '''

        agent_type = KlaraImporter.parse_agent_type(objectify.fromstring(xml))
        self.assertEqual(agent_type.cpf, AgentType.PERSON)
        self.assertEqual(agent_type.main_type.name, 'Nationell nivå')
        self.assertEqual(agent_type.sub_type, 'Person (släkt)')

    def test_parse_corporate_body(self):
        xml = '''
            <ArchiveOrig>
                <ObjectParts type="ValueMap">
                    <General type="ValueMap">
                        <ArchiveOrig.Parent.Name type="String">Nationell nivå</ArchiveOrig.Parent.Name>
                        <ArchOrigCategory.Name type="String">Corporate</ArchOrigCategory.Name>
                    </General>
                </ObjectParts>
            </ArchiveOrig>
        '''

        agent_type = KlaraImporter.parse_agent_type(objectify.fromstring(xml))
        self.assertEqual(agent_type.cpf, AgentType.CORPORATE_BODY)
        self.assertEqual(agent_type.main_type.name, 'Nationell nivå')
        self.assertEqual(agent_type.sub_type, 'Corporate')


class ParseAgentAlternativeNamesTests(TestCase):
    fixtures = ['countries_data', 'languages_data']

    @classmethod
    def setUpTestData(cls):
        cls.importer = KlaraImporter(None)

        main_type = MainAgentType.objects.create()
        agent_type = AgentType.objects.create(main_type=main_type)

        cls.agent = Agent.objects.create(
            type=agent_type,
            ref_code=cls.importer.ref_code,
            level_of_detail=Agent.MINIMAL,
            record_status=Agent.DRAFT,
            script=Agent.LATIN,
            language=cls.importer.language,
            create_date=timezone.now()
        )

    def test_parse_alternative_names(self):
        xml = '''
            <ArchiveOrig>
                <ObjectParts type="ValueMap">
                    <AltNames type="ValueMap">
                        <ArchiveOrig.AltNames rowCount="2" type="TableModel">
                            <ArchOrigAltName rowNo="0" type="RowMap">
                                <ArchOrigAltName.Name type="String">first</ArchOrigAltName.Name>
                                <ArchOrigAltName.UsedFrom type="String">1947</ArchOrigAltName.UsedFrom>
                                <ArchOrigAltName.UsedTo type="String">1974</ArchOrigAltName.UsedTo>
                            </ArchOrigAltName>
                            <ArchOrigAltName rowNo="1" type="RowMap">
                                <ArchOrigAltName.Name type="String">second</ArchOrigAltName.Name>
                                <ArchOrigAltName.UsedFrom type="String">1974</ArchOrigAltName.UsedFrom>
                                <ArchOrigAltName.UsedTo type="String">1995</ArchOrigAltName.UsedTo>
                            </ArchOrigAltName>
                        </ArchiveOrig.AltNames>
                    </AltNames>
                </ObjectParts>
            </ArchiveOrig>
        '''

        names = self.importer._parse_agent_alternative_names(
            objectify.fromstring(xml),
            self.agent,
            self.importer.alt_name_type,
        )

        self.assertEqual(len(list(names)), 2)
        self.assertEqual(
            AgentName.objects.filter(main="first", start_date="1947-01-01", end_date="1974-01-01").count(), 1
        )
        self.assertEqual(
            AgentName.objects.filter(main="second", start_date="1974-01-01", end_date="1995-01-01").count(), 1
        )
