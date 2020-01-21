import os
import shutil
import tempfile
from unittest import mock

from click.testing import CliRunner
from django.test import TestCase
from lxml import etree
from lxml.etree import DocumentInvalid

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.xml import (
    XMLISOSchematronValidator,
    XMLSchematronValidator,
    XMLSchemaValidator,
)
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.WorkflowEngine.models import ProcessTask


def create_mocked_error_log(line_number, error_msg):
    class MockedErrorLog:
        line = line_number
        message = error_msg

    return MockedErrorLog()


class XMLSchemaValidatorTests(TestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

        try:
            os.makedirs(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    @staticmethod
    def create_schema():
        return """<?xml version="1.0" encoding="UTF-8"?>
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
                    xmlns:tns="test/namespace" targetNamespace="test/namespace"
                    xmlns:xsd="http://www.w3.org/2001/XMLSchema">
            <xs:complexType name="itemtype">
              <xs:sequence>
                <xs:element name="title" type="xs:string"/>
                <xs:element name="price" type="xs:decimal"/>
              </xs:sequence>
            </xs:complexType>

            <xs:element name="item" type="tns:itemtype"/>
        </xs:schema>
        """

    def create_schema_file(self, path):
        path = os.path.join(self.datadir, path)

        with open(path, 'w') as f:
            f.write(self.create_schema())

        return path

    def create_schema_file_with_import(self, path):
        content = """<?xml version="1.0" encoding="UTF-8"?>
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
            <xs:import namespace="test/namespace"
                       schemaLocation="https://www.loc.gov/standards/mets/mets.xsd"/>
        </xs:schema>
        """
        path = os.path.join(self.datadir, path)

        with open(path, 'w') as f:
            f.write(content)

        return path

    def create_xml(self, xml_file_name):
        xml_file_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tns:item xmlns:tns="test/namespace">
            <title>good</title>
            <price>12.3</price>
        </tns:item>
        """

        xml_file_path = os.path.join(self.datadir, xml_file_name)

        with open(xml_file_path, 'w') as f:
            f.write(xml_file_content)

        return xml_file_path

    def create_bad_xml(self, xml_file_name):
        xml_file_content = """<?xml version="1.0" encoding="UTF-8"?>
        <tns:item xmlns:tns="test/namespace">
            <title>bad</title>
            <price>foo</price>
        </tns:item>
        """

        xml_file_path = os.path.join(self.datadir, xml_file_name)

        with open(xml_file_path, 'w') as f:
            f.write(xml_file_content)

        return xml_file_path

    def test_validate_schema_against_valid_file(self):
        schema_file_name = "schema.xsd"
        schema_file_path = self.create_schema_file(schema_file_name)
        xml_file_path = self.create_xml("xml_file.xml")

        validator = XMLSchemaValidator(
            context=schema_file_path,
            options={'rootdir': self.datadir},
        )
        validator.validate(xml_file_path)

    def test_validate_schema_against_bad_file(self):
        schema_file_name = "schema.xsd"
        schema_file_path = self.create_schema_file(schema_file_name)
        xml_file_path = self.create_bad_xml("bad_xml_file.xml")

        validator = XMLSchemaValidator(
            context=schema_file_path,
            options={'rootdir': self.datadir},
        )

        with self.assertRaises(ValidationError):
            validator.validate(xml_file_path)

        expected_error_message = "Element 'price': 'foo' is not a valid value of the atomic type 'xs:decimal'"
        self.assertTrue(Validation.objects.filter(message__icontains=expected_error_message).exists())

    def mock_download_schema(dirname, logger, schema, verify=None):
        path = os.path.join(dirname, 'foo.xsd')
        with open(path, 'w') as f:
            f.write(XMLSchemaValidatorTests.create_schema())
        return path

    @mock.patch('ESSArch_Core.ip.utils.download_schema', side_effect=mock_download_schema)
    def test_validate_with_imported_schema(self, mock_download):
        schema_file_name = "schema.xsd"
        schema_file_path = self.create_schema_file_with_import(schema_file_name)
        xml_file_path = self.create_xml("xml_file.xml")

        validator = XMLSchemaValidator(
            context=schema_file_path,
            options={'rootdir': self.datadir},
        )
        validator.validate(xml_file_path)
        mock_download.assert_called_once()

        mock_download.reset_mock()
        bad_xml_file_path = self.create_bad_xml("xml_file.xml")
        with self.assertRaises(ValidationError):
            validator.validate(bad_xml_file_path)

        mock_download.assert_called_once()

        expected_error_message = "Element 'price': 'foo' is not a valid value of the atomic type 'xs:decimal'"
        self.assertTrue(Validation.objects.filter(message__icontains=expected_error_message).exists())

        # ensure that the schema has only been modified in memory and not the file
        schema_doc = etree.parse(schema_file_path)
        schemaLocation = schema_doc.xpath('//*[local-name()="import"]/@schemaLocation')[0]
        self.assertEqual(schemaLocation, "https://www.loc.gov/standards/mets/mets.xsd")

    @mock.patch("ESSArch_Core.fixity.validation.backends.xml.validate_against_schema")
    def test_when_documentInvalid_raised_create_validation_objects(self, validate_against_schema):
        exception_obj = DocumentInvalid("error msg")
        exception_obj.error_log = [
            create_mocked_error_log(123, "error msg 1"),
            create_mocked_error_log(456, "error msg 2"),
        ]
        validate_against_schema.side_effect = mock.Mock(side_effect=exception_obj)

        ip = InformationPackage.objects.create()
        task = ProcessTask.objects.create(information_package=ip)

        validator = XMLSchemaValidator(
            context="dummy_schema.xsd",
            options={'rootdir': "dummy_rootdir"},
            ip=ip.id,
            task=task
        )
        with self.assertRaises(ValidationError):
            validator.validate("some_xml_file_path")

        validations = Validation.objects.filter(passed=False, validator="XMLSchemaValidator")
        self.assertEqual(validations.count(), 2)

    @mock.patch("ESSArch_Core.fixity.validation.backends.xml.validate_against_schema")
    def test_when_other_exception_raised_create_validation_object(self, validate_against_schema):
        exception_obj = Exception("error msg")
        validate_against_schema.side_effect = mock.Mock(side_effect=exception_obj)

        ip = InformationPackage.objects.create()
        task = ProcessTask.objects.create(information_package=ip)

        validator = XMLSchemaValidator(
            context="dummy_schema.xsd",
            options={'rootdir': "dummy_rootdir"},
            ip=ip.id,
            task=task
        )

        with self.assertRaises(Exception):
            validator.validate("some_xml_file_path")

        validations = Validation.objects.filter(
            information_package_id=ip.id,
            message='error msg',
            passed=False,
            task_id=task.id,
            validator='XMLSchemaValidator'
        )
        self.assertEqual(validations.count(), 1)

    @mock.patch("ESSArch_Core.fixity.validation.backends.xml.validate_against_schema")
    def test_when_successful_create_validation_object(self, validate_against_schema):
        ip = InformationPackage.objects.create()
        task = ProcessTask.objects.create(information_package=ip)

        validator = XMLSchemaValidator(
            context="dummy_schema.xsd",
            options={'rootdir': "dummy_rootdir"},
            ip=ip.id,
            task=task
        )

        validator.validate("some_xml_file_path")

        validations = Validation.objects.filter(
            information_package_id=ip.id,
            passed=True,
            task_id=task.id,
            validator='XMLSchemaValidator'
        )
        self.assertEqual(validations.count(), 1)

    @mock.patch("ESSArch_Core.fixity.validation.backends.xml.XMLSchemaValidator.validate")
    def test_cli(self, mock_validate):
        runner = CliRunner()
        with runner.isolated_filesystem():
            open('foo.xml', 'a')
            open('foo.xsd', 'a')
            with mock.patch("ESSArch_Core.fixity.validation.backends.xml.XMLSchemaValidator") as validator:
                result = runner.invoke(XMLSchemaValidator.cli, ['foo.xml', '--schema', 'foo.xsd'])
                validator.assert_called_once_with(context='foo.xsd')
                self.assertEqual(result.exit_code, 0)

            with mock.patch("ESSArch_Core.fixity.validation.backends.xml.XMLSchemaValidator.validate") as validate:
                result = runner.invoke(XMLSchemaValidator.cli, ['foo.xml', '--schema', 'foo.xsd'])
                validate.assert_called_once_with('foo.xml')
                self.assertEqual(result.exit_code, 0)


class XMLSchematronValidatorTests(TestCase):

    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

        try:
            os.makedirs(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def create_schematron_file(self, schematron_file_name):
        schematron_content = """<?xml version="1.0" encoding="UTF-8"?>
        <schema xmlns="http://www.ascc.net/xml/schematron">
            <ns uri="http://www.topologi.com/example" prefix="ex"/>
            <pattern name="Check structure">
                <rule context="ex:Person">
                    <assert test="@Title">The element Person must have a Title attribute</assert>
                    <assert test="count(ex:*) = 2 and count(ex:Name) = 1 and count(ex:Gender) = 1">
                    The element Person should have the child elements Name and Gender.</assert>
                    <assert test="ex:*[1] = ex:Name">The element Name must appear before element Gender.</assert>
                </rule>
            </pattern>
            <pattern name="Check co-occurrence constraints">
                <rule context="ex:Person">
                    <assert test="(@Title = 'Mr' and ex:Gender = 'Male') or @Title != 'Mr'">
                    If the Title is "Mr" then the gender of the person must be "Male".</assert>
                </rule>
            </pattern>
        </schema>
        """
        schematron_file_path = os.path.join(self.datadir, schematron_file_name)

        with open(schematron_file_path, 'w') as f:
            f.write(schematron_content)

        return schematron_file_path

    def create_xml(self, xml_file_name):
        xml_file_content = """<ex:Person Title="Mr" xmlns:ex="http://www.topologi.com/example">
            <ex:Name>Eddie</ex:Name>
            <ex:Gender>Male</ex:Gender>
        </ex:Person>
        """

        xml_file_path = os.path.join(self.datadir, xml_file_name)

        with open(xml_file_path, 'w') as f:
            f.write(xml_file_content)

        return xml_file_path

    def create_bad_xml(self, xml_file_name):
        xml_file_content = """<ex:Person Title="Mr" xmlns:ex="http://www.topologi.com/example"></ex:Person>"""

        xml_file_path = os.path.join(self.datadir, xml_file_name)

        with open(xml_file_path, 'w') as f:
            f.write(xml_file_content)

        return xml_file_path

    @mock.patch("ESSArch_Core.fixity.validation.backends.xml.XMLSchematronValidator._validate_schematron")
    def test_when_documentInvalid_raised_create_validation_objects(self, validate_schematron):
        exception_obj = DocumentInvalid("error msg")
        exception_obj.error_log = [
            create_mocked_error_log(123, "error msg 1"),
            create_mocked_error_log(456, "error msg 2"),
        ]
        validate_schematron.side_effect = mock.Mock(side_effect=exception_obj)

        ip = InformationPackage.objects.create()
        task = ProcessTask.objects.create(information_package=ip)

        validator = XMLSchematronValidator(
            context="dummy_schema.xsl",
            options={'rootdir': "dummy_rootdir"},
            ip=ip.id,
            task=task
        )
        with self.assertRaises(DocumentInvalid):
            validator.validate("some_xml_file_path")

        validations = Validation.objects.filter(passed=False, validator="XMLSchematronValidator")
        self.assertEqual(validations.count(), 2)

    @mock.patch("ESSArch_Core.fixity.validation.backends.xml.XMLSchematronValidator._validate_schematron")
    def test_when_other_exception_raised_create_validation_object(self, validate_against_schema):
        exception_obj = Exception("error msg")
        validate_against_schema.side_effect = mock.Mock(side_effect=exception_obj)

        ip = InformationPackage.objects.create()
        task = ProcessTask.objects.create(information_package=ip)

        validator = XMLSchematronValidator(
            context="dummy_schema.xsl",
            options={'rootdir': "dummy_rootdir"},
            ip=ip.id,
            task=task
        )

        with self.assertRaises(Exception):
            validator.validate("some_xml_file_path")

        validations = Validation.objects.filter(
            information_package_id=ip.id,
            message='error msg',
            passed=False,
            task_id=task.id,
            validator='XMLSchematronValidator'
        )
        self.assertEqual(validations.count(), 1)

    @mock.patch("ESSArch_Core.fixity.validation.backends.xml.XMLSchematronValidator._validate_schematron")
    def test_when_successful_create_validation_object(self, validate_against_schema):
        ip = InformationPackage.objects.create()
        task = ProcessTask.objects.create(information_package=ip)

        validator = XMLSchematronValidator(
            context="dummy_schema.xsl",
            options={'rootdir': "dummy_rootdir"},
            ip=ip.id,
            task=task
        )

        validator.validate("some_xml_file_path")

        validations = Validation.objects.filter(
            information_package_id=ip.id,
            passed=True,
            task_id=task.id,
            validator='XMLSchematronValidator'
        )
        self.assertEqual(validations.count(), 1)

    def test_validate_schematron_bad_schematron_file_should_raise_exception(self):
        schematron_file_name = "non_existing_schematron_file"
        schematron_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'{schematron_file_name}')
        xml_file_path = "dummy_file_path"

        validator = XMLSchematronValidator(
            context=schematron_file_path,
            options={'rootdir': "dummy_rootdir"},
            ip="dummy_ip_id",
            task="dummy_ip_id",
        )

        expected_error_message = f"Error reading file .*{schematron_file_name}'.* failed to load external entity"

        with self.assertRaisesRegexp(OSError, expected_error_message):
            validator._validate_schematron(xml_file_path)

    def test_validate_schematron_non_existing_file_path_should_raise_exception(self):
        schematron_file_name = "schematron.xsl"
        schematron_file_path = self.create_schematron_file(schematron_file_name)
        xml_file_path = "dummy_file_path"

        validator = XMLSchematronValidator(
            context=schematron_file_path,
            options={'rootdir': "dummy_rootdir"},
            ip="dummy_ip_id",
            task="dummy_ip_id",
        )

        expected_err_msg = f"Error reading file '{xml_file_path}': failed to load external entity \"{xml_file_path}\""

        with self.assertRaisesRegexp(OSError, expected_err_msg):
            validator._validate_schematron(xml_file_path)

    def test_validate_schematron_bad_file_should_raise_exception(self):
        schematron_file_name = "schematron.xsl"
        schematron_file_path = self.create_schematron_file(schematron_file_name)
        xml_file_path = self.create_bad_xml("bad_xml_file.xml")

        validator = XMLSchematronValidator(
            context=schematron_file_path,
            options={'rootdir': self.datadir},
            ip="dummy_ip_id",
            task="dummy_ip_id",
        )

        expected_error_message = ".*The element Person should have the child elements Name and Gender.*"

        with self.assertRaisesRegexp(DocumentInvalid, expected_error_message):
            validator._validate_schematron(xml_file_path)

    def test_validate_schematron_successful_validation_should_return(self):
        schematron_file_name = "schematron.xsl"
        schematron_file_path = self.create_schematron_file(schematron_file_name)
        xml_file_path = self.create_xml("xml_file.xml")

        validator = XMLSchematronValidator(
            context=schematron_file_path,
            options={'rootdir': self.datadir},
            ip="dummy_ip_id",
            task="dummy_ip_id",
        )

        validator._validate_schematron(xml_file_path)


class XMLISOSchematronValidatorTests(TestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

        try:
            os.makedirs(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def create_schematron_file(self, schematron_file_name):
        schematron_content = """<?xml version="1.0" encoding="UTF-8"?>
        <schema xmlns="http://purl.oclc.org/dsdl/schematron" >
            <ns uri="http://www.topologi.com/example" prefix="ex"/>
            <pattern id="Check_structure">
                <rule context="ex:Person">
                    <assert test="@Title">The element Person must have a Title attribute</assert>
                    <assert test="count(ex:*) = 2 and count(ex:Name) = 1 and count(ex:Gender) = 1">
                    The element Person should have the child elements Name and Gender.</assert>
                    <assert test="ex:*[1] = ex:Name">The element Name must appear before element Gender.</assert>
                </rule>
            </pattern>
            <pattern id="Check_co_occurrence_constraints">
                <rule context="ex:Person">
                    <assert test="(@Title = 'Mr' and ex:Gender = 'Male') or @Title != 'Mr'">
                    If the Title is "Mr" then the gender of the person must be "Male".</assert>
                </rule>
            </pattern>
        </schema>
        """
        schematron_file_path = os.path.join(self.datadir, schematron_file_name)

        with open(schematron_file_path, 'w') as f:
            f.write(schematron_content)

        return schematron_file_path

    def create_xml(self, xml_file_name):
        xml_file_content = """<ex:Person Title="Mr" xmlns:ex="http://www.topologi.com/example">
            <ex:Name>Eddie</ex:Name>
            <ex:Gender>Male</ex:Gender>
        </ex:Person>
        """

        xml_file_path = os.path.join(self.datadir, xml_file_name)

        with open(xml_file_path, 'w') as f:
            f.write(xml_file_content)

        return xml_file_path

    def create_bad_xml(self, xml_file_name):
        xml_file_content = """<ex:Person Title="Mr" xmlns:ex="http://www.topologi.com/example"></ex:Person>"""

        xml_file_path = os.path.join(self.datadir, xml_file_name)

        with open(xml_file_path, 'w') as f:
            f.write(xml_file_content)

        return xml_file_path

    @mock.patch("ESSArch_Core.fixity.validation.backends.xml.XMLISOSchematronValidator._validate_isoschematron")
    def test_when_documentInvalid_raised_create_validation_objects(self, validate_schematron):
        exception_obj = DocumentInvalid("error msg")
        exception_obj.error_log = [
            create_mocked_error_log(123, "error msg 1"),
            create_mocked_error_log(456, "error msg 2"),
        ]
        validate_schematron.side_effect = mock.Mock(side_effect=exception_obj)

        ip = InformationPackage.objects.create()
        task = ProcessTask.objects.create(information_package=ip)

        validator = XMLISOSchematronValidator(
            context="dummy_schema.xsl",
            options={'rootdir': "dummy_rootdir"},
            ip=ip.id,
            task=task
        )
        with self.assertRaises(DocumentInvalid):
            validator.validate("some_xml_file_path")

        validations = Validation.objects.filter(passed=False, validator="XMLISOSchematronValidator")
        self.assertEqual(validations.count(), 2)

    @mock.patch("ESSArch_Core.fixity.validation.backends.xml.XMLISOSchematronValidator._validate_isoschematron")
    def test_when_other_exception_raised_create_validation_object(self, validate_against_schema):
        exception_obj = Exception("error msg")
        validate_against_schema.side_effect = mock.Mock(side_effect=exception_obj)

        ip = InformationPackage.objects.create()
        task = ProcessTask.objects.create(information_package=ip)

        validator = XMLISOSchematronValidator(
            context="dummy_schema.xsl",
            options={'rootdir': "dummy_rootdir"},
            ip=ip.id,
            task=task
        )

        with self.assertRaises(Exception):
            validator.validate("some_xml_file_path")

        validations = Validation.objects.filter(
            information_package_id=ip.id,
            message='error msg',
            passed=False,
            task_id=task.id,
            validator='XMLISOSchematronValidator'
        )
        self.assertEqual(validations.count(), 1)

    @mock.patch("ESSArch_Core.fixity.validation.backends.xml.XMLISOSchematronValidator._validate_isoschematron")
    def test_when_successful_create_validation_object(self, validate_against_schema):
        ip = InformationPackage.objects.create()
        task = ProcessTask.objects.create(information_package=ip)

        validator = XMLISOSchematronValidator(
            context="dummy_schema.xsl",
            options={'rootdir': "dummy_rootdir"},
            ip=ip.id,
            task=task
        )

        validator.validate("some_xml_file_path")

        validations = Validation.objects.filter(
            information_package_id=ip.id,
            passed=True,
            task_id=task.id,
            validator='XMLISOSchematronValidator'
        )
        self.assertEqual(validations.count(), 1)

    def test_validate_schematron_bad_schematron_file_should_raise_exception(self):
        schematron_file_name = "non_existing_schematron_file"
        schematron_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'{schematron_file_name}')
        xml_file_path = "dummy_file_path"

        validator = XMLISOSchematronValidator(
            context=schematron_file_path,
            options={'rootdir': "dummy_rootdir"},
            ip="dummy_ip_id",
            task="dummy_ip_id",
        )

        expected_error_message = f"Error reading file .*{schematron_file_name}'.* failed to load external entity"

        with self.assertRaisesRegexp(OSError, expected_error_message):
            validator._validate_isoschematron(xml_file_path)

    def test_validate_schematron_non_existing_file_path_should_raise_exception(self):
        schematron_file_name = "schematron.xsl"
        schematron_file_path = self.create_schematron_file(schematron_file_name)
        xml_file_path = "dummy_file_path"

        validator = XMLISOSchematronValidator(
            context=schematron_file_path,
            options={'rootdir': "dummy_rootdir"},
            ip="dummy_ip_id",
            task="dummy_ip_id",
        )

        expected_err_msg = f"Error reading file '{xml_file_path}': failed to load external entity \"{xml_file_path}\""

        with self.assertRaisesRegexp(OSError, expected_err_msg):
            validator._validate_isoschematron(xml_file_path)

    def test_validate_schematron_bad_file_should_raise_exception(self):
        schematron_file_name = "schematron.xsl"
        schematron_file_path = self.create_schematron_file(schematron_file_name)
        xml_file_path = self.create_bad_xml("bad_xml_file.xml")

        validator = XMLISOSchematronValidator(
            context=schematron_file_path,
            options={'rootdir': self.datadir},
            ip="dummy_ip_id",
            task="dummy_ip_id",
        )

        expected_error_message = ".*The element Person should have the child elements Name and Gender.*"

        with self.assertRaisesRegexp(DocumentInvalid, expected_error_message):
            validator._validate_isoschematron(xml_file_path)

    def test_validate_schematron_successful_validation_should_return(self):
        schematron_file_name = "schematron.xsl"
        schematron_file_path = self.create_schematron_file(schematron_file_name)
        xml_file_path = self.create_xml("xml_file.xml")

        validator = XMLISOSchematronValidator(
            context=schematron_file_path,
            options={'rootdir': self.datadir},
            ip="dummy_ip_id",
            task="dummy_ip_id",
        )

        validator._validate_isoschematron(xml_file_path)
