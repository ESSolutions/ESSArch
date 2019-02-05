import tempfile
import shutil

from subprocess import PIPE

from unittest import mock
from django.test import TestCase
from lxml import objectify, etree

from ESSArch_Core.util import (
    convert_file,
    get_value_from_path,
    get_files_and_dirs,
    parse_content_range_header,
    flatten,
    getSchemas
)


class ConvertFileTests(TestCase):
    @mock.patch('ESSArch_Core.util.Popen')
    def test_non_zero_returncode(self, mock_popen):
        process_mock = mock.Mock()
        attrs = {'communicate.return_value': ('output', 'error'), 'returncode': 1}
        process_mock.configure_mock(**attrs)
        mock_popen.return_value = process_mock

        with self.assertRaises(ValueError):
            convert_file("test.docx", "pdf")

        cmd = 'unoconv -f %s -eSelectPdfVersion=1 "%s"' % ('pdf', 'test.docx')
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.util.os.path.isfile', return_value=False)
    @mock.patch('ESSArch_Core.util.Popen')
    def test_zero_returncode_with_no_file_created(self, mock_popen, mock_isfile):
        process_mock = mock.Mock()
        attrs = {'communicate.return_value': ('output', 'error'), 'returncode': 0}
        process_mock.configure_mock(**attrs)
        mock_popen.return_value = process_mock

        with self.assertRaises(ValueError):
            convert_file("test.docx", "pdf")

        cmd = 'unoconv -f %s -eSelectPdfVersion=1 "%s"' % ('pdf', 'test.docx')
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.util.os.path.isfile', return_value=True)
    @mock.patch('ESSArch_Core.util.Popen')
    def test_zero_returncode_with_file_created(self, mock_popen, mock_isfile):
        process_mock = mock.Mock()
        attrs = {'communicate.return_value': ('output', 'error'), 'returncode': 0}
        process_mock.configure_mock(**attrs)
        mock_popen.return_value = process_mock

        self.assertEqual(convert_file("test.docx", "pdf"), 'test.pdf')

        cmd = 'unoconv -f %s -eSelectPdfVersion=1 "%s"' % ('pdf', 'test.docx')
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)


class GetValueFromPathTest(TestCase):

    @staticmethod
    def get_simple_xml():
        return '''
                    <volym andraddat="2014-03-11T14:10:35">
                        <volnr>1</volnr>
                        <tid>2000 -- 2005</tid>
                        <utseende>utseende_text</utseende>
                        <anmerkningar>anmerkningar_text</anmerkningar>
                    </volym>
        '''

    def test_get_value_from_path_when_path_is_none(self):
        xml = self.get_simple_xml()
        root_xml = objectify.fromstring(xml)
        self.assertEqual(get_value_from_path(root_xml, None), None)

    def test_get_value_from_path_when_attribute_is_missing(self):
        xml = self.get_simple_xml()
        root_xml = objectify.fromstring(xml)
        self.assertEqual(get_value_from_path(root_xml, "anmerkningar@onetuhoent"), None)


class GetFilesAndDirsTest(TestCase):

    def test_get_files_and_dirs_none_existent_dir(self):
        self.assertEqual(get_files_and_dirs("this_folder_or_path_should_not_exist"), [])


class ParseContentRangeHeaderTest(TestCase):

    def test_parse_content_range_header(self):
        header = 'bytes 123-456/789'
        ref_start = 123
        ref_end = 456
        ref_total = 789

        (start, end, total) = parse_content_range_header(header)
        self.assertEqual(start, ref_start)
        self.assertEqual(end, ref_end)
        self.assertEqual(total, ref_total)

    def test_parse_content_range_header_with_bad_header(self):
        header = "bad header"
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError) as context:
            parse_content_range_header(header)

        self.assertTrue('Invalid Content-Range header' in str(context.exception))


class FlattenTest(TestCase):

    def test_flatten_list_of_lists(self):
        my_list = [
            list(range(1, 10)),
            list(range(10, 20)),
        ]

        result_list = list(range(1, 20))
        self.assertEqual(result_list, flatten(my_list))


class GetSchemasTest(TestCase):

    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

    def get_simple_valid_xml(self):
        tmp_file = tempfile.TemporaryFile(dir=self.datadir)
        tmp_file.write(b'<?xml version="1.0" encoding="ISO-8859-1"?>')
        tmp_file.write(b'<vaxml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                       b'xmlns="http://www.visualarkiv.se/vaxml/v6.1" '
                       b'xsi:schemaLocation="http://www.visualarkiv.se/vaxml/v6.1 '
                       b'http://www.visualarkiv.se/vaxml/v6.1/vaxml.xsd" created="2019-01-23T19:17:34" '
                       b'generator="Visual Arkiv 6.2 version 6.2.0.12" countrycode="SE"></vaxml>')
        tmp_file.seek(0)

        return tmp_file

    def get_bad_xml_file(self):
        tmp_file = tempfile.TemporaryFile(dir=self.datadir)
        tmp_file.write(b'Hello bad XML syntax!')
        tmp_file.seek(0)

        return tmp_file

    def test_get_schemas_from_doc(self):
        filename = self.get_simple_valid_xml()

        parser = etree.XMLParser(remove_blank_text=True)
        doc = etree.parse(filename, parser=parser)

        schema = getSchemas(doc=doc)
        self.assertTrue(type(schema) is etree.XMLSchema)

    def test_get_schema_from_file(self):
        schema = getSchemas(filename=self.get_simple_valid_xml())
        self.assertTrue(type(schema) is etree.XMLSchema)

    def test_get_schema_with_no_argument_should_throw_exception(self):
        with self.assertRaises(AttributeError) as context:
            getSchemas()

        self.assertTrue("'NoneType' object has no attribute 'getroot'" in str(context.exception))

    def test_get_schema_from_none_existing_file_should_raise_exception(self):
        filename = "this_file_hopefully_does_not_exist"

        with self.assertRaises(IOError):
            getSchemas(filename=filename)

    def test_get_schema_from_file_with_bad_input(self):
        fp = self.get_bad_xml_file()

        with self.assertRaises(etree.XMLSyntaxError):
            getSchemas(filename=fp)

