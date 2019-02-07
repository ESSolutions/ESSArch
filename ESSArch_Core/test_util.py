import tempfile
import shutil
import os
import datetime

from subprocess import PIPE

from unittest import mock
from django.test import TestCase
from lxml import objectify, etree
from rest_framework.exceptions import ValidationError, NotFound

from ESSArch_Core.util import (
    convert_file,
    get_value_from_path,
    get_files_and_dirs,
    parse_content_range_header,
    flatten,
    getSchemas,
    nested_lookup,
    list_files,
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
        self.assertEqual(get_value_from_path(root_xml, "anmerkningar@non_existing_attr"), None)


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
        with self.assertRaisesRegex(ValidationError, "Invalid Content-Range header"):
            parse_content_range_header(header)


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
        tmp_file.write(b'<xml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                       b'xmlns="http://www.example.com/example/v4.2" '
                       b'xsi:schemaLocation="http://www.example.com/example/v4.2 '
                       b'http://www.example.com/example/v4.2/example.xsd"></xml>')
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
        with self.assertRaisesRegexp(AttributeError, "'NoneType' object has no attribute 'getroot'"):
            getSchemas()

    def test_get_schema_from_none_existing_file_should_raise_exception(self):
        filename = "this_file_hopefully_does_not_exist"

        with self.assertRaises(IOError):
            getSchemas(filename=filename)

    def test_get_schema_from_file_with_bad_input(self):
        fp = self.get_bad_xml_file()

        with self.assertRaises(etree.XMLSyntaxError):
            getSchemas(filename=fp)


class NestedLookupTest(TestCase):
    def test_nested_lookup_dict_first_layer(self):
        my_dict = {"my_key": 42}

        self.assertEqual(42, next(nested_lookup('my_key', my_dict)))

    def test_nested_lookup_nested_dict_two_layer(self):
        my_dict = {"first_layer": {"my_key": 42}}

        self.assertEqual(42, next(nested_lookup('my_key', my_dict)))

    def test_nested_lookup_list_in_dict(self):
        my_dict = {"first_layer": [
            {"key_1": 1},
            {"key_2": 2},
            {"my_key": 42},
            {"key_3": 3},
        ]}

        self.assertEqual(42, next(nested_lookup('my_key', my_dict)))

    def test_nested_lookup_dict_in_list(self):
        my_list = [
            {"key_1": 1},
            {"key_2": 2},
            {"my_key": 42},
            {"key_3": 3},
        ]

        self.assertEqual(42, next(nested_lookup('my_key', my_list)))

    def test_nested_lookup_multiple_occurrences_should_return_all_of_them(self):
        my_list = {
            "first_layer": [
                {"my_key": 1},
                {"key_2": 2},
                {"my_key": 3},
            ],
            "second_layer": [
                {"key_3": 3},
                {"my_key": 5},
                {"key_4": 4},
                {"my_key": 7},
            ]
        }

        found_values = list(nested_lookup('my_key', my_list))
        self.assertEqual(len(found_values), 4)
        self.assertIn(1, found_values)
        self.assertIn(3, found_values)
        self.assertIn(5, found_values)
        self.assertIn(7, found_values)

    def test_nested_lookup_key_missing_should_return_None(self):
        my_list = [
            {"key_1": 1},
            {"key_2": 2},
            {"key_3": 3},
        ]

        result_list = list(nested_lookup('missing_key', my_list))
        self.assertEqual(len(result_list), 0)


class ListFilesTest(TestCase):

    def setUp(self):
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.textdir = os.path.join(self.datadir, "textdir")
        self.addCleanup(shutil.rmtree, self.datadir)

        try:
            os.makedirs(self.textdir)
        except OSError as e:
            if e.errno != 17:
                raise

    def create_files(self):
        files = []
        for i in range(3):
            fname = os.path.join(self.textdir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('%s' % i)
            files.append(fname)

        return files

    def create_archive_file(self, archive_format):
        self.create_files()

        output_filename = "archive_file"
        archive_file_full_path = os.path.join(self.datadir, output_filename)

        return shutil.make_archive(archive_file_full_path, archive_format, self.textdir)

    def test_list_files_dir_with_default_args_should_raise_NotFound(self):
        path = self.datadir
        self.create_files()

        with self.assertRaises(NotFound):
            list_files(path)

    def test_list_files_tarfile_with_default_args_should_return_response(self):
        file_path = self.create_archive_file('tar')
        resp = list_files(file_path)
        self.assertEqual(resp.status_code, 200)
        file_names = ["./0.txt", "./1.txt", "./2.txt"]  # TODO: bug in shutil for tar is adding an extra './'

        for el in resp.data:
            data_name = el['name']
            data_type = el['type']
            data_size = el['size']
            data_modified = el['modified']

            self.assertIn(data_name, file_names)
            file_names.remove(data_name)
            self.assertEqual(data_type, "file")
            self.assertEqual(data_size, 1)
            self.assertEqual(type(data_modified), datetime.datetime)

    def test_list_files_zip_file_with_default_args_should_return_response(self):
        file_path = self.create_archive_file('zip')
        resp = list_files(file_path)
        self.assertEqual(resp.status_code, 200)
        file_names = ["0.txt", "1.txt", "2.txt"]

        for el in resp.data:
            data_name = el['name']
            data_type = el['type']
            data_size = el['size']
            data_modified = el['modified']

            self.assertIn(data_name, file_names)
            file_names.remove(data_name)
            self.assertEqual(data_type, "file")
            self.assertEqual(data_size, 1)
            self.assertEqual(type(data_modified), datetime.datetime)

    @mock.patch('ESSArch_Core.util.generate_file_response')
    def test_list_files_path_to_file_in_tar(self, generate_file_response):
        file_path = self.create_archive_file('tar')
        sub_path_file = './0.txt'  # TODO: bug in shutil for tar is adding an extra './'
        new_folder = os.path.join(file_path, sub_path_file)

        list_files(new_folder)

        generate_file_response.assert_called_once_with(mock.ANY, 'text/plain', False, name=sub_path_file)

    def test_list_files_path_to_non_existing_file_in_tar_should_throw_NotFound(self):
        file_path = self.create_archive_file('tar')
        new_folder = os.path.join(file_path, "non_existing_file.txt")

        with self.assertRaises(NotFound):
            list_files(new_folder)

    def test_list_files_path_to_non_existing_file_in_zip_should_throw_NotFound(self):
        file_path = self.create_archive_file('zip')
        new_folder = os.path.join(file_path, "non_existing_file.txt")

        with self.assertRaises(NotFound):
            list_files(new_folder)

    @mock.patch('ESSArch_Core.util.generate_file_response')
    def test_list_files_path_to_file_in_zip(self, generate_file_response):
        file_path = self.create_archive_file('zip')
        sub_path_file = '0.txt'
        new_folder = os.path.join(file_path, sub_path_file)

        list_files(new_folder)

        generate_file_response.assert_called_once_with(mock.ANY, 'text/plain', False, name=sub_path_file)
