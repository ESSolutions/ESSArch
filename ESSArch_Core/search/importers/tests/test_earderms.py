import os
import shutil
import tempfile
import uuid
from unittest import mock

from django.test import TestCase
from lxml import etree

from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.search.importers.earderms import (
    EardErmsImporter,
    get_encoded_content_from_file,
)
from ESSArch_Core.tags.documents import InnerArchiveDocument
from ESSArch_Core.tags.models import (
    Structure,
    StructureType,
    StructureUnit,
    StructureUnitType,
)
from ESSArch_Core.WorkflowEngine.models import ProcessTask


def get_xml_example_full():
    dirname = os.path.dirname(os.path.abspath(__file__))
    path_to_example_xml = os.path.join(dirname, "earderms_full_example.xml")
    with open(path_to_example_xml, 'r') as f:
        xml_content = f.read()
    return bytes(xml_content, 'utf-8')


def get_xml_root_from_string(xml_string):
    return etree.fromstring(xml_string, etree.XMLParser(remove_blank_text=True))


class GetErrandsRootTests(TestCase):

    def setUp(self):
        self.importer = EardErmsImporter(None)

    def test_get_errands_root_full_xml(self):
        root = get_xml_root_from_string(get_xml_example_full())

        res = self.importer.get_errands_root(root)

        elem = res[0]
        self.assertEqual(len(res), 1)
        self.assertEqual(type(elem), etree._Element)
        self.assertEqual(elem.tag, 'ArkivobjektListaArenden')

    def test_get_errands_root_simple(self):
        xml_string = '''
            <root>
                <ArkivobjektListaArenden></ArkivobjektListaArenden>
            </root>
        '''
        root = get_xml_root_from_string(xml_string)

        res = self.importer.get_errands_root(root)

        elem = res[0]
        self.assertEqual(len(res), 1)
        self.assertEqual(type(elem), etree._Element)
        self.assertEqual(elem.tag, 'ArkivobjektListaArenden')

    def test_get_errands_root_simple_should_be_in_root(self):
        xml_string = '''
            <root>
                <Leveransobjekt>
                    <ArkivobjektListaArenden></ArkivobjektListaArenden>
                </Leveransobjekt>
            </root>
        '''
        root = get_xml_root_from_string(xml_string)

        res = self.importer.get_errands_root(root)

        self.assertEqual(res, [])


class GetActsRootTests(TestCase):

    def setUp(self):
        self.importer = EardErmsImporter(None)

    def get_arkivobjekt_arende(self):
        return get_xml_root_from_string(get_xml_example_full()) \
            .xpath("*[local-name()='ArkivobjektListaArenden']")[0] \
            .xpath("*[local-name()='ArkivobjektArende']")[0]

    def test_get_acts_root_full_xml(self):
        root = self.get_arkivobjekt_arende()
        res = self.importer.get_acts_root(root)

        elem = res[0]
        self.assertEqual(len(res), 1)
        self.assertEqual(type(elem), etree._Element)
        self.assertEqual(elem.tag, 'ArkivobjektListaHandlingar')

    def test_get_acts_root_simple(self):
        xml_string = '''
            <root>
                <ArkivobjektListaHandlingar></ArkivobjektListaHandlingar>
            </root>
        '''
        root = get_xml_root_from_string(xml_string)

        res = self.importer.get_acts_root(root)

        elem = res[0]
        self.assertEqual(len(res), 1)
        self.assertEqual(type(elem), etree._Element)
        self.assertEqual(elem.tag, 'ArkivobjektListaHandlingar')

    def test_get_acts_root_simple_should_be_in_root(self):
        xml_string = '''
            <root>
                <ArkivobjektArende>
                    <ArkivobjektListaHandlingar></ArkivobjektListaHandlingar>
                </ArkivobjektArende>
            </root>
        '''
        root = get_xml_root_from_string(xml_string)

        res = self.importer.get_acts_root(root)

        self.assertEqual(res, [])


class GetArkivObjektArendenTests(TestCase):

    def setUp(self):
        self.importer = EardErmsImporter(None)

    def get_arkiv_objekt_lista_arenden(self):
        return get_xml_root_from_string(get_xml_example_full()) \
            .xpath("*[local-name()='ArkivobjektListaArenden']")[0]

    def test_get_arkiv_objekt_arenden_full_xml(self):
        root = self.get_arkiv_objekt_lista_arenden()
        res = self.importer.get_arkiv_objekt_arenden(root)

        elem = res[0]
        self.assertEqual(len(res), 1)
        self.assertEqual(type(elem), etree._Element)
        self.assertEqual(elem.tag, 'ArkivobjektArende')

    def test_get_arkiv_objekt_arenden_simple(self):
        xml_string = '''
            <root>
                <ArkivobjektArende></ArkivobjektArende>
            </root>
        '''
        root = get_xml_root_from_string(xml_string)

        res = self.importer.get_arkiv_objekt_arenden(root)

        elem = res[0]
        self.assertEqual(len(res), 1)
        self.assertEqual(type(elem), etree._Element)
        self.assertEqual(elem.tag, 'ArkivobjektArende')

    def test_get_arkiv_objekt_arenden_simple_should_be_in_root(self):
        xml_string = '''
            <root>
                <ArkivobjektListaArenden>
                    <ArkivobjektArende></ArkivobjektArende>
                </ArkivobjektListaArenden>
            </root>
        '''
        root = get_xml_root_from_string(xml_string)

        res = self.importer.get_arkiv_objekt_arenden(root)

        self.assertEqual(res, [])


class ParsePersonTests(TestCase):

    def setUp(self):
        self.importer = EardErmsImporter(None)

    def test_parse_person_simple_success(self):
        xml_string = '''
            <root>
                <Namn>some name</Namn>
                <Organisation>some org</Organisation>
                <Postadress>some post address</Postadress>
                <Postnummer>some post number</Postnummer>
                <Postort>some post ort</Postort>
                <Lang>some lang</Lang>
                <IDnummer>some idnr</IDnummer>
                <Telefon>12345</Telefon>
                <Fax>67890</Fax>
                <EPost>some@epost.at</EPost>
                <SkyddadIdentitet>secret person</SkyddadIdentitet>
            </root>
        '''

        expected_data = {
            'namn': 'some name',
            'organisation': 'some org',
            'postadress': 'some post address',
            'postnummer': 'some post number',
            'postort': 'some post ort',
            'land': 'some lang',
            'id': 'some idnr',
            'telefon': '12345',
            'fax': '67890',
            'epost': 'some@epost.at',
            'skyddad_identitet': 'secret person',
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_person(root)

        self.assertDictEqual(data, expected_data)

    def test_parse_person_with_not_all_keys_should_catch_indexError(self):
        xml_string = '''
            <root>
                <Namn>some name</Namn>
                <Organisation>some org</Organisation>
                <Postadress>some post address</Postadress>
            </root>
        '''

        expected_data = {
            'namn': 'some name',
            'organisation': 'some org',
            'postadress': 'some post address',
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_person(root)

        self.assertDictEqual(data, expected_data)


class ParseAgentTests(TestCase):

    def setUp(self):
        self.importer = EardErmsImporter(None)

    def test_parse_agent_simple_success(self):
        xml_string = '''
            <root>
                <Namn>some name</Namn>
                <Roll>some roll</Roll>
                <Enhetsnamn>some enhet</Enhetsnamn>
                <Organisationsnamn>some org</Organisationsnamn>
            </root>
        '''

        expected_data = {
            'namn': 'some name',
            'roll': 'some roll',
            'enhet': 'some enhet',
            'organisation': 'some org',
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_agent(root)

        self.assertDictEqual(data, expected_data)

    def test_parse_agent_with_not_all_keys_should_catch_indexError(self):
        xml_string = '''
            <root>
                <Namn>some name</Namn>
                <Roll>some roll</Roll>
            </root>
        '''

        expected_data = {
            'namn': 'some name',
            'roll': 'some roll',
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_agent(root)

        self.assertDictEqual(data, expected_data)


class ParseRelationTests(TestCase):

    def setUp(self):
        self.importer = EardErmsImporter(None)

    def test_parse_relation_should_get_type(self):
        xml_string = '''<root Typ='some pre-defined type' AnnanTyp='other type'>some reference text</root>'''

        expected_data = {
            'typ': 'some pre-defined type',
            'referens': 'some reference text',
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_relation(root)

        self.assertDictEqual(data, expected_data)

    def test_parse_relation_should_get_AnnanTyp(self):
        xml_string = '''<root Typ='Egen relationsdefinition' AnnanTyp='other type'>some reference text</root>'''

        expected_data = {
            'typ': 'other type',
            'referens': 'some reference text',
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_relation(root)

        self.assertDictEqual(data, expected_data)


class ParseExtraIdTests(TestCase):

    def setUp(self):
        self.importer = EardErmsImporter(None)

    def test_parse_extra_id_with_no_text_should_return_None(self):
        xml_string = '''<root ExtraIDTyp='some id type'></root>'''

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_extra_id(root)

        self.assertIsNone(data)

    def test_parse_extra_id_with_text_should_get_type_and_id(self):
        xml_string = '''<root ExtraIDTyp='some id type'>some_id_text</root>'''

        expected_data = {
            'typ': 'some id type',
            'id': 'some_id_text',
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_extra_id(root)

        self.assertDictEqual(data, expected_data)


class ParseInitiatorTests(TestCase):

    def setUp(self):
        self.importer = EardErmsImporter(None)

    def test_parse_initiator_all_attributes_success(self):
        xml_string = '''
            <root>
                <subroot>
                    <Egenskap Namn='Namn'><Varde>some name</Varde></Egenskap>
                    <Egenskap Namn='Adress'><Varde>some post address</Varde></Egenskap>
                    <Egenskap Namn='Postnummer'><Varde>some zipcode</Varde></Egenskap>
                    <Egenskap Namn='Postort'><Varde>some post ort</Varde></Egenskap>
                    <Egenskap Namn='Personnummer'><Varde>some id nr</Varde></Egenskap>
                    <Egenskap Namn='Telefon'><Varde>12345</Varde></Egenskap>
                    <Egenskap Namn='Mobil'><Varde>67890</Varde></Egenskap>
                    <Egenskap Namn='E-post'><Varde>some@epost.at</Varde></Egenskap>
                </subroot>
            </root>
        '''

        expected_data = {
            'name': 'some name',
            'address': 'some post address',
            'zipcode': 'some zipcode',
            'city': 'some post ort',
            'personal_identification_number': 'some id nr',
            'phone': '12345',
            'mobile_phone': '67890',
            'email': 'some@epost.at',
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_initiator(root)

        self.assertDictEqual(data, expected_data)

    def test_parse_initiator_with_not_all_keys_should_catch_indexError_and_continue(self):
        xml_string = '''
            <root>
                <subroot>
                    <Egenskap Namn='Namn'><Varde>some name</Varde></Egenskap>
                    <Egenskap Namn='Adress'><Varde>some post address</Varde></Egenskap>
                    <Egenskap Namn='Postnummer'><Varde>some zipcode</Varde></Egenskap>
                </subroot>
            </root>
        '''

        expected_data = {
            'name': 'some name',
            'address': 'some post address',
            'zipcode': 'some zipcode',
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_initiator(root)

        self.assertDictEqual(data, expected_data)


class ParseRestrictionTests(TestCase):

    def setUp(self):
        self.importer = EardErmsImporter(None)

    def test_parse_restriction_without_AnnanTyp_attr_should_get_Typ_and_all_texts(self):
        xml_string = '''
            <root Typ='some type'>
                <ForklarandeText>some desc text</ForklarandeText>
                <Lagrum>some lagrum</Lagrum>
                <RestriktionsDatum>some expiration date</RestriktionsDatum>
            </root>
        '''

        expected_data = {
            'beskrivning': 'some desc text',
            'lagrum': 'some lagrum',
            'upphor': 'some expiration date',
            'typ': 'some type'
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_restriction(root)

        self.assertDictEqual(data, expected_data)

    def test_parse_restriction_without_some_keys_should_catch_IndexError_and_continue(self):
        xml_string = '''
            <root Typ='some type'>
                <ForklarandeText>some desc text</ForklarandeText>
                <Lagrum>some lagrum</Lagrum>
            </root>
        '''

        expected_data = {
            'beskrivning': 'some desc text',
            'lagrum': 'some lagrum',
            'typ': 'some type'
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_restriction(root)

        self.assertDictEqual(data, expected_data)

    def test_parse_restriction_with_AnnanTyp_attr_should_get_AnnanTyp_and_all_texts(self):
        xml_string = '''
            <root Typ='some type' AnnanTyp='some other type'>
                <ForklarandeText>some desc text</ForklarandeText>
                <Lagrum>some lagrum</Lagrum>
                <RestriktionsDatum>some expiration date</RestriktionsDatum>
            </root>
        '''

        expected_data = {
            'beskrivning': 'some desc text',
            'lagrum': 'some lagrum',
            'upphor': 'some expiration date',
            'typ': 'some other type'
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_restriction(root)

        self.assertDictEqual(data, expected_data)


class ParseGallringTests(TestCase):

    def setUp(self):
        self.importer = EardErmsImporter(None)

    def test_parse_gallring_when_gallras_is_true(self):
        xml_string = '''
            <root Gallras='true'>
                <GallringsFrist>some g deadline</GallringsFrist>
                <GallringsForklaring>some g desc</GallringsForklaring>
                <GallringsPeriodSlut>some period end</GallringsPeriodSlut>
            </root>
        '''

        expected_data = {
            'frist': 'some g deadline',
            'forklaring': 'some g desc',
            'period_slut': 'some period end',
            'gallras': True,
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_gallring(root)

        self.assertDictEqual(data, expected_data)

    def test_parse_gallring_when_gallras_is_false(self):
        xml_string = '''
            <root gallras='false'>
                <GallringsFrist>some g deadline</GallringsFrist>
                <GallringsForklaring>some g desc</GallringsForklaring>
                <GallringsPeriodSlut>some period end</GallringsPeriodSlut>
            </root>
        '''

        expected_data = {
            'frist': 'some g deadline',
            'forklaring': 'some g desc',
            'period_slut': 'some period end',
            'gallras': False,
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_gallring(root)

        self.assertDictEqual(data, expected_data)

    def test_parse_gallring_when_not_all_keys_exists_should_catch_IndexError_and_continue(self):
        xml_string = '''
            <root gallras='false'>
                <GallringsFrist>some g deadline</GallringsFrist>
                <GallringsForklaring>some g desc</GallringsForklaring>
            </root>
        '''

        expected_data = {
            'frist': 'some g deadline',
            'forklaring': 'some g desc',
            'gallras': False,
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_gallring(root)

        self.assertDictEqual(data, expected_data)


class ParseEgenskaperTests(TestCase):

    def setUp(self):
        self.importer = EardErmsImporter(None)

    def test_parse_egenskaper_with_one_level_of_egenskaper(self):
        xml_string = '''
            <root Namn='some name' DataTyp='some data type' Format='some format'>
                <Varde>some value</Varde>
            </root>
        '''

        expected_data = {
            'varde': 'some value',
            'namn': 'some name',
            'datatyp': 'some data type',
            'format': 'some format',
            'egenskaper': [],
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_egenskaper(root)

        self.assertDictEqual(data, expected_data)

    def test_parse_egenskaper_with_two_levels_of_egenskaper(self):
        xml_string = '''
            <root Namn='some name' DataTyp='some data type' Format='some format'>
                <Varde>some value</Varde>
                <Egenskaper>
                    <Egenskap Namn='sub name 1' DataTyp='sub data type 1' Format='sub format 1'>
                        <Varde>sub value 1</Varde>
                    </Egenskap>
                    <Egenskap Namn='sub name 2' DataTyp='sub data type 2' Format='sub format 2'>
                        <Varde>sub value 2</Varde>
                    </Egenskap>
                </Egenskaper>
            </root>
        '''

        expected_data = {
            'varde': 'some value',
            'namn': 'some name',
            'datatyp': 'some data type',
            'format': 'some format',
            'egenskaper': [
                {
                    'varde': 'sub value 1',
                    'namn': 'sub name 1',
                    'datatyp': 'sub data type 1',
                    'format': 'sub format 1',
                    'egenskaper': []
                },
                {
                    'varde': 'sub value 2',
                    'namn': 'sub name 2',
                    'datatyp': 'sub data type 2',
                    'format': 'sub format 2',
                    'egenskaper': []
                },
            ],
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_egenskaper(root)

        self.assertDictEqual(data, expected_data)


class ParseEgetElementTests(TestCase):

    def setUp(self):
        self.importer = EardErmsImporter(None)

    def test_parse_eget_element_with_one_level_of_element(self):
        xml_string = '''
            <root Namn='some name' DataTyp='some data type' Format='some format'>
                <Varde>some value</Varde>
            </root>
        '''

        expected_data = {
            'varde': 'some value',
            'namn': 'some name',
            'datatyp': 'some data type',
            'format': 'some format',
            'element': [],
            'egenskaper': [],
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_eget_element(root)

        self.assertDictEqual(data, expected_data)

    def test_parse_eget_element_with_no_Namn_attribute(self):
        xml_string = '''
            <root DataTyp='some data type' Format='some format'>
                <Varde>some value</Varde>
            </root>
        '''

        expected_data = {
            'varde': 'some value',
            'namn': None,
            'datatyp': 'some data type',
            'format': 'some format',
            'element': [],
            'egenskaper': [],
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_eget_element(root)

        self.assertDictEqual(data, expected_data)

    def test_parse_eget_element_with_egenskaper(self):
        self.importer.parse_egenskaper = mock.Mock(return_value={'dummy_egenskap': 'dummy_value'})
        xml_string = '''
            <root Namn='some name' DataTyp='some data type' Format='some format'>
                <Varde>some value</Varde>
                <Egenskaper>
                    <Egenskap>
                    </Egenskap>
                </Egenskaper>
            </root>
        '''

        expected_data = {
            'varde': 'some value',
            'namn': 'some name',
            'datatyp': 'some data type',
            'format': 'some format',
            'element': [],
            'egenskaper': [{'dummy_egenskap': 'dummy_value'}],
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_eget_element(root)

        self.assertDictEqual(data, expected_data)

    def test_parse_eget_element_with_name_prefix_should_remove_the_prefix(self):
        xml_string = '''
            <root Namn='Dokument/Ärende/some name' DataTyp='some data type' Format='some format'>
                <Varde>some value</Varde>
            </root>
        '''

        expected_data = {
            'varde': 'some value',
            'namn': 'some name',
            'datatyp': 'some data type',
            'format': 'some format',
            'element': [],
            'egenskaper': [],
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_eget_element(root)

        self.assertDictEqual(data, expected_data)

    def test_parse_eget_element_with_two_levels_of_element(self):
        xml_string = '''
            <root Namn='some name' DataTyp='some data type' Format='some format'>
                <Varde>some value</Varde>
                <EgetElement Namn='sub name 1' DataTyp='sub data type 1' Format='sub format 1'>
                    <Varde>sub value 1</Varde>
                </EgetElement>
                <EgetElement Namn='sub name 2' DataTyp='sub data type 2' Format='sub format 2'>
                    <Varde>sub value 2</Varde>
                </EgetElement>
            </root>
        '''

        expected_data = {
            'varde': 'some value',
            'namn': 'some name',
            'datatyp': 'some data type',
            'format': 'some format',
            'element': [
                {
                    'varde': 'sub value 1',
                    'namn': 'sub name 1',
                    'datatyp': 'sub data type 1',
                    'format': 'sub format 1',
                    'egenskaper': [],
                    'element': [],
                },
                {
                    'varde': 'sub value 2',
                    'namn': 'sub name 2',
                    'datatyp': 'sub data type 2',
                    'format': 'sub format 2',
                    'egenskaper': [],
                    'element': [],
                },
            ],
            'egenskaper': [],
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_eget_element(root)

        self.assertDictEqual(data, expected_data)


class ParseEgnaElementTests(TestCase):

    def setUp(self):
        self.importer = EardErmsImporter(None)

    def test_parse_egna_element_with_one_level_of_element(self):
        xml_string = '''
            <root Namn='some name' DataTyp='some data type' Format='some format'>
                <EgnaElementBeskrivning>some description</EgnaElementBeskrivning>
            </root>
        '''

        expected_data = {
            'beskrivning': 'some description',
            'element': [],
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_egna_element(root)

        self.assertDictEqual(data, expected_data)

    def test_parse_egna_element_with_element(self):
        self.importer.parse_eget_element = mock.Mock(return_value={'dummy_element': 'dummy_value'})
        xml_string = '''
            <root Namn='some name' DataTyp='some data type' Format='some format'>
                <EgnaElementBeskrivning>some description</EgnaElementBeskrivning>
                <EgetElement></EgetElement>
            </root>
        '''

        expected_data = {
            'beskrivning': 'some description',
            'element': [{'dummy_element': 'dummy_value'}],
        }

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_egna_element(root)

        self.assertDictEqual(data, expected_data)


class ParseMappingsTests(TestCase):

    def setUp(self):
        self.importer = EardErmsImporter(None)

    def test_parse_mappings_single_elements(self):
        xml_string = '''
            <root>
                <Bar>some text</Bar>
            </root>
        '''

        mappings = {'bar': 'Bar'}

        expected_data = {'bar': 'some text'}

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_mappings(mappings, root)

        self.assertDictEqual(data, expected_data)

    def test_parse_mappings_missing_key_should_catch_IndexError_and_continue(self):
        xml_string = '''
            <root>
                <Foo>some foo text</Foo>
                <Bar>some bar text</Bar>
            </root>
        '''

        mappings = {
            'bar': 'Bar',
            'foobar': 'Foobar',
        }

        expected_data = {'bar': 'some bar text'}

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_mappings(mappings, root)

        self.assertDictEqual(data, expected_data)

    def test_parse_mappings_multiple_values_should_return_the_first_mappings_value(self):
        xml_string = '''
            <root>
                <Foo>some foo text</Foo>
                <Bar>some bar text</Bar>
            </root>
        '''

        mappings = {'any_foo_bar': ['Bar', 'Foo']}

        expected_data = {'any_foo_bar': 'some bar text'}

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_mappings(mappings, root)

        self.assertDictEqual(data, expected_data)

    def test_parse_mappings_multiple_if_first_not_found_get_next_value(self):
        xml_string = '''
            <root>
                <Foo>some foo text</Foo>
            </root>
        '''

        mappings = {'any_foo_bar': ['Bar', 'Foo']}

        expected_data = {'any_foo_bar': 'some foo text'}

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_mappings(mappings, root)

        self.assertDictEqual(data, expected_data)

    def test_parse_mappings_if_no_element_found_should_return_empty_dict(self):
        xml_string = '''
            <root>
                <Foo>some foo text</Foo>
                <Foobar>some foo text</Foobar>
            </root>
        '''

        mappings = {'bar': 'Bar'}

        expected_data = {}

        root = get_xml_root_from_string(xml_string)
        data = self.importer.parse_mappings(mappings, root)

        self.assertDictEqual(data, expected_data)


class ParseErrandTests(TestCase):

    def setUp(self):
        self.importer = EardErmsImporter(None)
        self.archive = mock.Mock()
        self.archive.pk = uuid.uuid4()
        self.ip = InformationPackage.objects.create()
        self.importer.task = ProcessTask.objects.create()
        self.structure_type = StructureType.objects.create(name="test")
        self.structure = Structure.objects.create(type=self.structure_type, is_template=False)
        self.structure_unit_type = StructureUnitType.objects.create(name="test", structure_type=self.structure_type)
        self.structure_unit = StructureUnit.objects.create(
            type=self.structure_unit_type,
            structure=self.structure,
            reference_code='some_klass_ref_2'
        )

    @mock.patch('ESSArch_Core.search.importers.earderms.logger')
    def test_parse_errand_when_no_structure_unit_exists_then_raise_exception(self, mock_logger):

        xml_string = '''
            <root>
                <ArkivobjektID>some_id</ArkivobjektID>
                <KlassReferens>some_ref</KlassReferens>
            </root>
        '''

        root = get_xml_root_from_string(xml_string)
        with self.assertRaises(StructureUnit.DoesNotExist):
            self.importer.parse_errand(root, self.archive, self.ip, None)

        mock_logger.exception.assert_called_once_with('Structure unit some_ref not found in None')

    def test_parse_errand_when_all_elements_exists(self):
        root = self.get_arkiv_objekt_arende()
        component, structure_unit = self.importer.parse_errand(root, self.archive, self.ip, self.structure)

        self.assertEqual(structure_unit, self.structure_unit)

    def get_arkiv_objekt_arende(self):
        return get_xml_root_from_string(get_xml_example_full()) \
            .xpath("*[local-name()='ArkivobjektListaArenden']")[0] \
            .xpath("*[local-name()='ArkivobjektArende']")[0]

    def test_parse_errand_when_only_the_elementary_elements_exists(self):
        xml_string = '''
            <root>
                <ArkivobjektID>some_id</ArkivobjektID>
                <KlassReferens>some_klass_ref_2</KlassReferens>
            </root>
        '''

        root = get_xml_root_from_string(xml_string)
        component, structure_unit = self.importer.parse_errand(root, self.archive, self.ip, self.structure)

        self.assertEqual(structure_unit, self.structure_unit)

    def test_parse_errand_when_all_elements_exists_and_ip_is_None(self):
        root = self.get_arkiv_objekt_arende()
        component, structure_unit = self.importer.parse_errand(root, self.archive, None, self.structure)

        self.assertEqual(structure_unit, self.structure_unit)

    def test_parse_errand_when_element_Motpart_is_missing_should_pass(self):
        root = self.get_arkiv_objekt_arende()

        # Remove 'Motpart' tag
        motpart = root.xpath("*[local-name()='Motpart']")[0]
        motpart.getparent().remove(motpart)
        # Make sure there is no more 'Motpart'
        self.assertEqual(root.xpath("*[local-name()='Motpart']"), [])

        component, structure_unit = self.importer.parse_errand(root, self.archive, self.ip, self.structure)

        self.assertEqual(structure_unit, self.structure_unit)


class ParseActTests(TestCase):

    def setUp(self):
        self.importer = EardErmsImporter(None)
        self.archive = mock.Mock()
        self.archive.pk = uuid.uuid4()
        self.ip = InformationPackage.objects.create()
        self.importer.task = ProcessTask.objects.create()
        self.errand = mock.Mock()
        self.errand.meta.id = 'some_errand_meta_id'
        self.errand._index._name = 'some_errand_index_name'
        self.errand.archive = InnerArchiveDocument.from_obj(self.archive)
        self.errand.ip = self.ip.pk

    def get_arkivobjekt_handling(self):
        return get_xml_root_from_string(get_xml_example_full()) \
            .xpath("*[local-name()='ArkivobjektListaHandlingar']")[0] \
            .xpath("*[local-name()='ArkivobjektHandling']")[0]

    def test_parse_act(self):
        root = self.get_arkivobjekt_handling()
        self.importer.parse_act(root, self.errand, self.ip)

    def test_parse_act_when_Gallring_element_is_missing_should_catch_the_exception_and_continue(self):
        root = self.get_arkivobjekt_handling()

        # Remove 'Gallring' tag
        gallring = root.xpath("*[local-name()='Gallring']")[0]
        gallring.getparent().remove(gallring)
        # Make sure there is no more 'Gallring'
        self.assertEqual(root.xpath("*[local-name()='Gallring']"), [])

        tag_version = self.importer.parse_act(root, self.errand, self.ip)
        self.assertIsNone(tag_version.custom_fields.get('gallring'))

    def test_parse_act_when_ExtraID_tag_has_no_text_then_should_not_add_to_data(self):
        root = self.get_arkivobjekt_handling()

        # Remove text for 'ExtraID' tag
        root.xpath("*[local-name()='ExtraID']")[0].clear()
        # Make sure 'ExtraID' text is cleared
        self.assertIsNone(root.xpath("*[local-name()='ExtraID']")[0].text)

        tag_version = self.importer.parse_act(root, self.errand, self.ip)

        # Check that all expected data is part of the component.
        self.assertEqual(tag_version.custom_fields.get('extra_ids'), [])


class GetEncodedContentFromFileTests(TestCase):

    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.file_with_ascii_content = os.path.join(self.datadir, 'my_ascii_file')
        self.addCleanup(shutil.rmtree, self.datadir)
        self.expected_encoded_content = "aGVsbG8gYXNjaWkgd29ybGQ="

        try:
            line = 'hello ascii world'
            with open(self.file_with_ascii_content, 'w', encoding='ascii') as f:
                f.write(line)
        except OSError as e:
            if e.errno != 17:
                raise

    def test_get_encoded_file_is_b64_ascii(self):
        res = get_encoded_content_from_file(self.file_with_ascii_content)
        self.assertEqual(res, self.expected_encoded_content)
