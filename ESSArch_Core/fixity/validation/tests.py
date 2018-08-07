import errno
import hashlib
import os
import shutil
import tempfile

from django.test import SimpleTestCase, TestCase
from lxml import etree
from pyfakefs import fake_filesystem_unittest

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.essxml import Generator
from ESSArch_Core.essxml.Generator.xmlGenerator import XMLGenerator
from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.format import FormatIdentifier
from ESSArch_Core.fixity.validation.backends.checksum import ChecksumValidator
from ESSArch_Core.fixity.validation.backends.format import FormatValidator
from ESSArch_Core.fixity.validation.backends.structure import StructureValidator
from ESSArch_Core.fixity.validation.backends.xml import DiffCheckValidator, XMLComparisonValidator


class ChecksumValidatorTests(fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.test_file = 'foo.txt'
        self.content = 'test file'
        with open(self.test_file, 'wb') as f:
            f.write(self.content)

        md5 = hashlib.md5(self.content)
        self.checksum = md5.hexdigest()

    def test_validate_against_string(self):
        options = {'expected': self.checksum}
        self.validator = ChecksumValidator(context='checksum_str', options=options)
        self.validator.validate(self.test_file)

        self.validator.options = {'expected': 'incorrect'}
        with self.assertRaises(ValidationError):
            self.validator.validate(self.test_file)

    def test_validate_against_checksum_file(self):
        checksum_file = '%s.md5' % self.test_file
        options = {'expected': checksum_file}
        with open(checksum_file, 'wb') as f:
            f.write(self.checksum)

        self.validator = ChecksumValidator(context='checksum_file', options=options)
        self.validator.validate(self.test_file)

        with open(checksum_file, 'a') as f:
            f.write('appended')

        with self.assertRaises(ValidationError):
            self.validator.validate(self.test_file)


class ChecksumValidatorXMLTests(SimpleTestCase):
    """
    pyfakefs doesn't support lxml, need separate test case without pyfakefs:
    https://github.com/jmcgeheeiv/pyfakefs#compatibility
    """

    def setUp(self):
        self.content = 'test file'
        md5 = hashlib.md5(self.content)
        self.checksum = md5.hexdigest()

        self.test_file = tempfile.NamedTemporaryFile()
        self.test_file.write(self.content)
        self.test_file.seek(0)

        self.xml_file = tempfile.NamedTemporaryFile()

    def test_validate_against_xml_file_valid(self):
        xml_str = '<root><file CHECKSUM="{hash}" CHECKSUMTYPE="{alg}"><FLocat href="{file}"/></file></root>'.format(
            hash=self.checksum, alg='md5', file=self.test_file.name)
        self.xml_file.write(xml_str)
        self.xml_file.seek(0)

        options = {'expected': self.xml_file.name, 'algorithm': 'md5'}
        self.validator = ChecksumValidator(context='xml_file', options=options)
        self.validator.validate(self.test_file.name)

    def test_validate_against_xml_file_invalid(self):
        xml_str = '<root><file CHECKSUM="{hash}" CHECKSUMTYPE="{alg}"><FLocat href="{file}"/></file></root>'.format(
            hash=self.checksum + 'appended', alg='md5', file=self.test_file.name)
        self.xml_file.write(xml_str)
        self.xml_file.seek(0)

        options = {'expected': self.xml_file.name, 'algorithm': 'md5'}
        self.validator = ChecksumValidator(context='xml_file', options=options)

        with self.assertRaises(ValidationError):
            self.validator.validate(self.test_file.name)

    def test_validate_against_xml_file_with_multiple_files(self):
        content2 = 'test file 2'
        md5 = hashlib.md5(content2)
        checksum2 = md5.hexdigest()

        test_file2 = tempfile.NamedTemporaryFile()
        test_file2.write(content2)
        test_file2.seek(0)

        xml_str = '''
            <root>
                <file CHECKSUM="{hash}" CHECKSUMTYPE="{alg}">
                    <FLocat href="{file}"/>
                </file>
                <file CHECKSUM="{hash2}" CHECKSUMTYPE="{alg}">
                    <FLocat href="{file2}"/>
                </file>
            </root>'''.format(
                    hash=self.checksum, alg='md5', file=self.test_file.name,
                    hash2=checksum2, file2=test_file2.name)
        self.xml_file.write(xml_str)
        self.xml_file.seek(0)

        options = {'expected': self.xml_file.name, 'algorithm': 'md5'}
        self.validator = ChecksumValidator(context='xml_file', options=options)

        self.validator.validate(self.test_file.name)
        self.validator.validate(test_file2.name)


class StructureValidatorTests(SimpleTestCase):
class FormatValidatorTests(TestCase):
    def setUp(self):
        self.content = 'test file'
        self.test_file = tempfile.NamedTemporaryFile(suffix='.txt')
        self.test_file.write(self.content)
        self.test_file.seek(0)

        mimetypes_path = os.path.join(os.path.dirname(Generator.__file__), 'mime.types')
        Path.objects.create(entity="path_mimetypes_definitionfile", value=mimetypes_path)

        fid = FormatIdentifier()
        self.expected = fid.identify_file_format(self.test_file.name)

    def test_validate(self):
        self.validator = FormatValidator()
        self.validator.validate(self.test_file.name, self.expected)

        with self.assertRaises(ValidationError):
            self.validator.validate(self.test_file.name, ('incorrect', None, None))


class StructureValidatorTests(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.validator_class = StructureValidator

    def tearDown(self):
        try:
            shutil.rmtree(self.root)
        except OSError as exc:
            if exc.errno != errno.ENOENT:
                raise

    def test_validate_allow_empty_false(self):
        options = {
            'tree': [
                {
                    "type": "root",
                    "allow_empty": False
                }
            ]
        }
        validator = self.validator_class(options=options)

        with self.assertRaises(ValidationError):
            validator.validate(self.root)

        open(os.path.join(self.root, 'foo.txt'), 'a').close()
        validator.validate(self.root)

    def test_validate_allow_empty_true(self):
        options = {
            'tree': [
                {
                    "type": "root",
                    "allow_empty": True
                }
            ]
        }
        validator = self.validator_class(options=options)
        validator.validate(self.root)
        open(os.path.join(self.root, 'foo.txt'), 'a').close()
        validator.validate(self.root)

    def test_validate_allow_empty_nested_dir(self):
        options = {
            'tree': [
                {
                    "type": "folder",
                    "name": "dir1",
                    "allow_empty": True
                },
                {
                    "type": "folder",
                    "name": "dir2",
                    "allow_empty": False
                },
            ]
        }
        os.mkdir(os.path.join(self.root, 'dir1'))
        os.mkdir(os.path.join(self.root, 'dir2'))
        validator = self.validator_class(options=options)
        with self.assertRaises(ValidationError):
            validator.validate(self.root)

        open(os.path.join(self.root, 'dir1', 'foo.txt'), 'a').close()
        with self.assertRaises(ValidationError):
            validator.validate(self.root)

        open(os.path.join(self.root, 'dir2', 'foo.txt'), 'a').close()
        validator.validate(self.root)

    def test_validate_required_files(self):
        options = {
            'tree': [
                {
                    "type": "root",
                    "required_files": ["foo.txt", "bar.txt"]
                }
            ]
        }

        validator = self.validator_class(options=options)

        with self.assertRaises(ValidationError):
            validator.validate(self.root)

        open(os.path.join(self.root, 'foo.txt'), 'a').close()

        with self.assertRaises(ValidationError):
            validator.validate(self.root)

        open(os.path.join(self.root, 'additional.txt'), 'a').close()

        with self.assertRaises(ValidationError):
            validator.validate(self.root)

        open(os.path.join(self.root, 'bar.txt'), 'a').close()

        validator.validate(self.root)

    def test_valid_paths(self):
        options = {
            'tree': [
                {
                    "type": "root",
                    "valid_paths": ["*.txt", "*.pdf"]
                }
            ]
        }

        validator = self.validator_class(options=options)

        validator.validate(self.root)

        open(os.path.join(self.root, 'foo.txt'), 'a').close()
        validator.validate(self.root)

        open(os.path.join(self.root, 'bar.pdf'), 'a').close()
        validator.validate(self.root)

        open(os.path.join(self.root, 'invalid.exe'), 'a').close()
        with self.assertRaises(ValidationError):
            validator.validate(self.root)

    def test_valid_paths_and_required_files(self):
        options = {
            'tree': [
                {
                    "type": "root",
                    "required_files": ["foo.txt"],
                    "valid_paths": ["*.pdf"]
                }
            ]
        }

        validator = self.validator_class(options=options)

        # empty
        with self.assertRaises(ValidationError):
            validator.validate(self.root)

        # add required file
        open(os.path.join(self.root, 'foo.txt'), 'a').close()
        validator.validate(self.root)

    def test_valid_related_paths(self):
        options = {
            'tree': [
                {
                    "type": "root",
                    "valid_paths": [["*.txt", "*.pdf"], "*.xml"]
                }
            ]
        }
        validator = self.validator_class(options=options)

        # empty
        validator.validate(self.root)

        # only xml
        open(os.path.join(self.root, 'test.xml'), 'a').close()
        validator.validate(self.root)

        # txt without related pdf
        open(os.path.join(self.root, 'foo.txt'), 'a').close()
        with self.assertRaisesRegexp(ValidationError, 'foo.txt missing related file foo.pdf'):
            validator.validate(self.root)

        # pdf with wrong name added
        open(os.path.join(self.root, 'bar.pdf'), 'a').close()
        try:
            with self.assertRaisesRegexp(ValidationError, 'foo.txt missing related file foo.pdf'):
                validator.validate(self.root)
        except AssertionError:
            # ordering of files (especially on Windows)
            with self.assertRaisesRegexp(ValidationError, 'bar.pdf missing related file bar.txt'):
                validator.validate(self.root)
        os.remove(os.path.join(self.root, 'bar.pdf'))

        # pdf added
        open(os.path.join(self.root, 'foo.pdf'), 'a').close()
        validator.validate(self.root)

        # txt deleted
        os.remove(os.path.join(self.root, 'foo.txt'))
        with self.assertRaisesRegexp(ValidationError, 'foo.pdf missing related file foo.txt'):
            validator.validate(self.root)

    def test_valid_multiple_related_paths(self):
        options = {
            'tree': [
                {
                    "type": "root",
                    "valid_paths": [["*.mkv", "*.mkv.md5"], ["*.txt", "*.pdf"]]
                }
            ]
        }
        validator = self.validator_class(options=options)

        # empty
        validator.validate(self.root)

        # add mkv
        open(os.path.join(self.root, 'foo.mkv'), 'a').close()
        with self.assertRaisesRegexp(ValidationError, 'foo.mkv missing related file foo.mkv.md5'):
            validator.validate(self.root)

        # add txt
        open(os.path.join(self.root, 'foo.txt'), 'a').close()
        with self.assertRaisesRegexp(ValidationError, 'foo.mkv missing related file foo.mkv.md5'):
            validator.validate(self.root)

        # add mkv.md5
        open(os.path.join(self.root, 'foo.mkv.md5'), 'a').close()
        with self.assertRaisesRegexp(ValidationError, 'foo.txt missing related file foo.pdf'):
            validator.validate(self.root)

        # add pdf
        open(os.path.join(self.root, 'foo.pdf'), 'a').close()
        validator.validate(self.root)

    def test_valid_related_paths_different_folders(self):
        os.mkdir(os.path.join(self.root, 'c'))
        os.mkdir(os.path.join(self.root, 'p'))

        options = {
            'tree': [
                {
                    "type": "root",
                    "valid_paths": [["c/*.mkv", "c/*.mkv.md5", "p/*.mp4", "p/*.mp4.md5"]]
                }
            ]
        }
        validator = self.validator_class(options=options)

        # empty
        validator.validate(self.root)

        # add mkv
        open(os.path.join(self.root, 'c/test.mkv'), 'a').close()
        with self.assertRaisesRegexp(ValidationError, 'c/test.mkv missing related file c/test.mkv.md5'):
            validator.validate(self.root)

        # add mkv.md5
        open(os.path.join(self.root, 'c/test.mkv.md5'), 'a').close()
        with self.assertRaisesRegexp(ValidationError, 'c/test.mkv missing related file p/test.mp4'):
            validator.validate(self.root)

        # add mp4
        open(os.path.join(self.root, 'p/test.mp4'), 'a').close()
        with self.assertRaisesRegexp(ValidationError, 'c/test.mkv missing related file p/test.mp4.md5'):
            validator.validate(self.root)

        # add mp4.md5
        open(os.path.join(self.root, 'p/test.mp4.md5'), 'a').close()
        validator.validate(self.root)


class DiffCheckValidatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        mimetypes_path = os.path.join(os.path.dirname(Generator.__file__), 'mime.types')
        Path.objects.create(entity="path_mimetypes_definitionfile", value=mimetypes_path)
        cls.generator = XMLGenerator()

    @classmethod
    def tearDownClass(cls):
        Path.objects.all().delete()

    def setUp(self):
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.xml')
        self.options = {'rootdir': self.datadir}

        self.filesToCreate = {
            self.fname: {
                'data': {},
                'spec': {
                    '-name': 'root',
                    '-children': [
                        {
                            "-name": "file",
                            "-containsFiles": True,
                            "-attr": [
                                {
                                    "-name": "MIMETYPE",
                                    "#content": "{{FMimetype}}",
                                },
                                {
                                    "-name": "CHECKSUM",
                                    "#content": "{{FChecksum}}"
                                },
                                {
                                    "-name": "CHECKSUMTYPE",
                                    "#content": "{{FChecksumType}}"
                                },
                                {
                                    "-name": "SIZE",
                                    "#content": "{{FSize}}"
                                }
                            ],
                            "-children": [
                                {
                                    "-name": "FLocat",
                                    "-attr": [
                                        {
                                            "-name": "href",
                                            "-namespace": "xlink",
                                            "#content": "file:///{{href}}"
                                        },
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
        }

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def create_files(self):
        files = []
        for i in range(3):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('%s' % i)
            files.append(fname)

        return files

    def generate_xml(self):
        self.generator.generate(self.filesToCreate, folderToParse=self.datadir)

    def test_validation_without_files(self):
        root = etree.fromstring('<root></root>')

        with open(self.fname, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        self.validator.validate(self.datadir)

    def test_validation_with_unchanged_files(self):
        files = self.create_files()
        self.generate_xml()

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        self.validator.validate(self.datadir)

    def test_validation_with_unchanged_files_multiple_times(self):
        files = self.create_files()
        self.generate_xml()

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        self.validator.validate(self.datadir)
        self.validator.validate(self.datadir)

    def test_validation_with_unchanged_files_with_same_content(self):
        files = [os.path.join(self.datadir, 'first.txt'), os.path.join(self.datadir, 'second.txt')]

        for f in files:
            with open(f, 'w') as fp:
                fp.write('foo')

        self.generate_xml()

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        self.validator.validate(self.datadir)

    def test_validation_with_unchanged_file_in_directory(self):
        os.mkdir(os.path.join(self.datadir, 'dir1'))
        files = [os.path.join(self.datadir, 'dir1', 'first.txt')]

        for f in files:
            with open(f, 'w') as fp:
                fp.write('foo')

        self.generate_xml()

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        self.validator.validate(self.datadir)

    def test_validation_with_deleted_file(self):
        files = self.create_files()
        self.generate_xml()
        os.remove(files[0])

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        msg = '2 confirmed, 0 added, 0 changed, 0 renamed, 1 deleted$'.format(xml=self.fname)
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.datadir)

    def test_validation_with_added_file(self):
        files = self.create_files()
        self.generate_xml()

        added = os.path.join(self.datadir, 'added.txt')
        with open(added, 'w') as f:
            f.write('added')

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        msg = '3 confirmed, 1 added, 0 changed, 0 renamed, 0 deleted$'.format(xml=self.fname)
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.datadir)

    def test_validation_with_renamed_file(self):
        files = self.create_files()
        self.generate_xml()

        old = files[0]
        new = os.path.join(self.datadir, 'new.txt')
        os.rename(old, new)

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        msg = '2 confirmed, 0 added, 0 changed, 1 renamed, 0 deleted$'.format(xml=self.fname)
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.datadir)

    def test_validation_with_changed_file(self):
        files = self.create_files()
        self.generate_xml()

        with open(files[0], 'a') as f:
            f.write('changed')

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        msg = '2 confirmed, 0 added, 1 changed, 0 renamed, 0 deleted$'.format(xml=self.fname)
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.datadir)

    def test_validation_with_checksum_attribute_missing(self):
        files = self.create_files()
        self.generate_xml()

        tree = etree.parse(self.fname)
        file_el = tree.xpath('*[local-name()="file"]')[1]
        file_el.attrib.pop('CHECKSUM')
        tree.write(self.fname, xml_declaration=True, encoding='UTF-8')

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        msg = '2 confirmed, 0 added, 1 changed, 0 renamed, 0 deleted$'.format(xml=self.fname)
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.datadir)

    def test_validation_with_incorrect_size(self):
        files = self.create_files()
        self.generate_xml()

        tree = etree.parse(self.fname)
        file_el = tree.xpath('*[local-name()="file"]')[1]
        file_el.attrib['SIZE'] = str(os.path.getsize(files[1])*2)
        tree.write(self.fname, xml_declaration=True, encoding='UTF-8')

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        msg = '2 confirmed, 0 added, 1 changed, 0 renamed, 0 deleted$'.format(xml=self.fname)
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.datadir)

    def test_validation_with_size_attribute_missing(self):
        files = self.create_files()
        self.generate_xml()

        tree = etree.parse(self.fname)
        file_el = tree.xpath('*[local-name()="file"]')[1]
        file_el.attrib.pop('SIZE')
        tree.write(self.fname, xml_declaration=True, encoding='UTF-8')

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        self.validator.validate(self.datadir)

    def test_validation_two_identical_files_one_missing(self):
        files = []
        for i in range(2):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('foo')
            files.append(fname)
        self.generate_xml()
        os.remove(files[0])

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        msg = '1 confirmed, 0 added, 0 changed, 0 renamed, 1 deleted$'.format(xml=self.fname)
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.datadir)

    def test_validation_two_identical_files_one_renamed(self):
        files = []
        for i in range(2):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('foo')
            files.append(fname)
        self.generate_xml()

        old = files[0]
        new = os.path.join(self.datadir, 'new.txt')
        os.rename(old, new)

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        msg = '1 confirmed, 0 added, 0 changed, 1 renamed, 0 deleted$'.format(xml=self.fname)
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.datadir)

    def test_validation_two_identical_files_one_renamed_one_deleted(self):
        files = []
        for i in range(2):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('foo')
            files.append(fname)
        self.generate_xml()

        old = files[0]
        new = os.path.join(self.datadir, 'new.txt')
        os.rename(old, new)

        os.remove(files[1])

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        msg = '0 confirmed, 0 added, 0 changed, 1 renamed, 1 deleted$'.format(xml=self.fname)
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.datadir)

    def test_validation_three_identical_files_two_renamed_one_deleted(self):
        files = []
        for i in range(3):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('foo')
            files.append(fname)
        self.generate_xml()

        old = files[0]
        new = os.path.join(self.datadir, 'new.txt')
        os.rename(old, new)

        old = files[1]
        new = os.path.join(self.datadir, 'newer.txt')
        os.rename(old, new)

        os.remove(files[2])

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        msg = '0 confirmed, 0 added, 0 changed, 2 renamed, 1 deleted$'.format(xml=self.fname)
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.datadir)

    def test_validation_three_identical_files_two_renamed_one_added(self):
        files = []
        for i in range(3):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('foo')
            files.append(fname)
        self.generate_xml()

        old = files[0]
        new = os.path.join(self.datadir, 'new.txt')
        os.rename(old, new)

        old = files[1]
        new = os.path.join(self.datadir, 'newer.txt')
        os.rename(old, new)

        added = os.path.join(self.datadir, 'added.txt')
        with open(added, 'w') as f:
            f.write('foo')

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        msg = '1 confirmed, 1 added, 0 changed, 2 renamed, 0 deleted$'.format(xml=self.fname)
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.datadir)

    def test_validation_two_identical_files_one_changed(self):
        files = []
        for i in range(2):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('foo')
            files.append(fname)
        self.generate_xml()

        with open(files[0], 'a') as f:
            f.write('changed')

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        msg = '1 confirmed, 0 added, 1 changed, 0 renamed, 0 deleted$'.format(xml=self.fname)
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.datadir)

    def test_validation_with_added_identical_file(self):
        files = self.create_files()
        self.generate_xml()

        added = os.path.join(self.datadir, 'added.txt')
        with open(added, 'w') as f:
            with open(files[1]) as f1:
                f.write(f1.read())

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        msg = '3 confirmed, 1 added, 0 changed, 0 renamed, 0 deleted$'.format(xml=self.fname)
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.datadir)

    def test_validation_with_added_identical_file_reversed_walk(self):
        files = self.create_files()
        self.generate_xml()

        added = os.path.join(self.datadir, 'added.txt')
        with open(added, 'w') as f:
            with open(files[1]) as f1:
                f.write(f1.read())
        for f in files:
            os.remove(f)
        self.create_files()

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        msg = '3 confirmed, 1 added, 0 changed, 0 renamed, 0 deleted$'.format(xml=self.fname)
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.datadir)

    def test_validation_with_all_alterations(self):
        files = self.create_files()
        self.generate_xml()

        with open(files[0], 'a') as f:
            f.write('changed')
        os.remove(files[1])
        os.rename(files[2], os.path.join(self.datadir, 'new.txt'))
        added = os.path.join(self.datadir, 'added.txt')
        with open(added, 'w') as f:
            f.write('added')

        self.validator = DiffCheckValidator(context=self.fname, options=self.options)
        msg = '0 confirmed, 1 added, 1 changed, 1 renamed, 1 deleted$'.format(xml=self.fname)
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.datadir)


class XMLComparisonValidatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        mimetypes_path = os.path.join(os.path.dirname(Generator.__file__), 'mime.types')
        Path.objects.create(entity="path_mimetypes_definitionfile", value=mimetypes_path)
        cls.generator = XMLGenerator()

    @classmethod
    def tearDownClass(cls):
        Path.objects.all().delete()

    def setUp(self):
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.xmldir = os.path.join(self.datadir, "metadata")
        self.mets = os.path.join(self.xmldir, 'mets.xml')
        self.premis = os.path.join(self.xmldir, 'premis.xml')
        self.options = {'rootdir': self.datadir}

        self.mets_spec = {
            self.mets: {
                'data': {},
                'spec': {
                    '-name': 'root',
                    '-children': [
                        {
                            "-name": "file",
                            "-containsFiles": True,
                            "-attr": [
                                {
                                    "-name": "MIMETYPE",
                                    "#content": "{{FMimetype}}",
                                },
                                {
                                    "-name": "CHECKSUM",
                                    "#content": "{{FChecksum}}"
                                },
                                {
                                    "-name": "CHECKSUMTYPE",
                                    "#content": "{{FChecksumType}}"
                                },
                                {
                                    "-name": "SIZE",
                                    "#content": "{{FSize}}"
                                }
                            ],
                            "-children": [
                                {
                                    "-name": "FLocat",
                                    "-attr": [
                                        {
                                            "-name": "href",
                                            "-namespace": "xlink",
                                            "#content": "file:///{{href}}"
                                        },
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
        }

        self.premis_spec = {
            self.premis: {
                'data': {},
                'spec': {
                    '-name': 'root',
                    '-children': [
                        {
                            "-name": "file",
                            "-containsFiles": True,
                            "-attr": [
                                {
                                    "-name": "MIMETYPE",
                                    "#content": "{{FMimetype}}",
                                },
                                {
                                    "-name": "CHECKSUM",
                                    "#content": "{{FChecksum}}"
                                },
                                {
                                    "-name": "CHECKSUMTYPE",
                                    "#content": "{{FChecksumType}}"
                                },
                                {
                                    "-name": "SIZE",
                                    "#content": "{{FSize}}"
                                }
                            ],
                            "-children": [
                                {
                                    "-name": "FLocat",
                                    "-attr": [
                                        {
                                            "-name": "href",
                                            "-namespace": "xlink",
                                            "#content": "file:///{{href}}"
                                        },
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
        }

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

        try:
            os.mkdir(self.xmldir)
        except OSError as e:
            if e.errno != 17:
                raise

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def create_files(self):
        files = []
        for i in range(3):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('%s' % i)
            files.append(fname)

        return files

    def generate_mets_xml(self):
        self.generator.generate(self.mets_spec, folderToParse=self.datadir)

    def generate_premis_xml(self):
        self.generator.generate(self.premis_spec, folderToParse=self.datadir)

    def test_validation_without_files(self):
        root = etree.fromstring('<root></root>')

        with open(self.mets, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))
        with open(self.premis, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        self.validator.validate(self.premis)

    def test_validation_with_unchanged_files(self):
        files = self.create_files()
        self.generate_mets_xml()
        self.generate_premis_xml()

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        self.validator.validate(self.premis)

    def test_validation_with_unchanged_files_multiple_times(self):
        files = self.create_files()
        self.generate_mets_xml()
        self.generate_premis_xml()

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        self.validator.validate(self.premis)
        self.validator.validate(self.premis)

    def test_validation_with_unchanged_files_with_same_content(self):
        files = [os.path.join(self.datadir, 'first.txt'), os.path.join(self.datadir, 'second.txt')]

        for f in files:
            with open(os.path.join(f), 'w') as fp:
                fp.write('foo')

        self.generate_mets_xml()
        self.generate_premis_xml()

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        self.validator.validate(self.premis)

    def test_validation_with_deleted_file(self):
        files = self.create_files()
        self.generate_mets_xml()
        os.remove(files[0])
        self.generate_premis_xml()

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        msg = '2 confirmed, 0 added, 0 changed, 0 renamed, 1 deleted$'
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.premis)

    def test_validation_with_added_file(self):
        files = self.create_files()
        self.generate_mets_xml()

        added = os.path.join(self.datadir, 'added.txt')
        with open(added, 'w') as f:
            f.write('added')
        self.generate_premis_xml()

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        msg = '3 confirmed, 1 added, 0 changed, 0 renamed, 0 deleted$'
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.premis)

    def test_validation_with_renamed_file(self):
        files = self.create_files()
        self.generate_mets_xml()

        old = files[0]
        new = os.path.join(self.datadir, 'new.txt')
        os.rename(old, new)
        self.generate_premis_xml()

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        msg = '2 confirmed, 0 added, 0 changed, 1 renamed, 0 deleted$'
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.premis)

    def test_validation_with_changed_file(self):
        files = self.create_files()
        self.generate_mets_xml()

        with open(files[0], 'a') as f:
            f.write('changed')
        self.generate_premis_xml()

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        msg = '2 confirmed, 0 added, 1 changed, 0 renamed, 0 deleted$'
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.premis)

    def test_validation_with_checksum_attribute_missing(self):
        files = self.create_files()
        self.generate_mets_xml()
        self.generate_premis_xml()

        tree = etree.parse(self.premis)
        file_el = tree.xpath('*[local-name()="file"]')[1]
        file_el.attrib.pop('CHECKSUM')
        tree.write(self.premis, xml_declaration=True, encoding='UTF-8')

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        msg = '2 confirmed, 0 added, 1 changed, 0 renamed, 0 deleted$'
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.premis)

    def test_validation_with_incorrect_size(self):
        files = self.create_files()
        self.generate_mets_xml()
        self.generate_premis_xml()

        tree = etree.parse(self.premis)
        file_el = tree.xpath('*[local-name()="file"]')[1]
        file_el.attrib['SIZE'] = str(os.path.getsize(files[1])*2)
        tree.write(self.premis, xml_declaration=True, encoding='UTF-8')

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        msg = '2 confirmed, 0 added, 1 changed, 0 renamed, 0 deleted$'
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.premis)

    def test_validation_with_size_attribute_missing(self):
        files = self.create_files()
        self.generate_mets_xml()
        self.generate_premis_xml()

        tree = etree.parse(self.premis)
        file_el = tree.xpath('*[local-name()="file"]')[1]
        file_el.attrib.pop('SIZE')
        tree.write(self.premis, xml_declaration=True, encoding='UTF-8')

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        self.validator.validate(self.premis)

    def test_validation_two_identical_files_one_missing(self):
        files = []
        for i in range(2):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('foo')
            files.append(fname)
        self.generate_mets_xml()
        os.remove(files[0])
        self.generate_premis_xml()

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        msg = '1 confirmed, 0 added, 0 changed, 0 renamed, 1 deleted$'
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.premis)

    def test_validation_two_identical_files_one_renamed(self):
        files = []
        for i in range(2):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('foo')
            files.append(fname)
        self.generate_mets_xml()

        old = files[0]
        new = os.path.join(self.datadir, 'new.txt')
        os.rename(old, new)
        self.generate_premis_xml()

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        msg = '1 confirmed, 0 added, 0 changed, 1 renamed, 0 deleted$'
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.premis)

    def test_validation_two_identical_files_one_renamed_one_deleted(self):
        files = []
        for i in range(2):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('foo')
            files.append(fname)
        self.generate_mets_xml()

        old = files[0]
        new = os.path.join(self.datadir, 'new.txt')
        os.rename(old, new)

        os.remove(files[1])
        self.generate_premis_xml()

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        msg = '0 confirmed, 0 added, 0 changed, 1 renamed, 1 deleted$'
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.premis)

    def test_validation_three_identical_files_two_renamed_one_deleted(self):
        files = []
        for i in range(3):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('foo')
            files.append(fname)
        self.generate_mets_xml()

        old = files[0]
        new = os.path.join(self.datadir, 'new.txt')
        os.rename(old, new)

        old = files[1]
        new = os.path.join(self.datadir, 'newer.txt')
        os.rename(old, new)

        os.remove(files[2])
        self.generate_premis_xml()

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        msg = '0 confirmed, 0 added, 0 changed, 2 renamed, 1 deleted$'
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.premis)

    def test_validation_three_identical_files_two_renamed_one_added(self):
        files = []
        for i in range(3):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('foo')
            files.append(fname)
        self.generate_mets_xml()

        old = files[0]
        new = os.path.join(self.datadir, 'new.txt')
        os.rename(old, new)

        old = files[1]
        new = os.path.join(self.datadir, 'newer.txt')
        os.rename(old, new)

        added = os.path.join(self.datadir, 'added.txt')
        with open(added, 'w') as f:
            f.write('foo')
        self.generate_premis_xml()

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        msg = '1 confirmed, 1 added, 0 changed, 2 renamed, 0 deleted$'
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.premis)

    def test_validation_two_identical_files_one_changed(self):
        files = []
        for i in range(2):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('foo')
            files.append(fname)
        self.generate_mets_xml()

        with open(files[0], 'a') as f:
            f.write('changed')
        self.generate_premis_xml()

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        msg = '1 confirmed, 0 added, 1 changed, 0 renamed, 0 deleted$'
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.premis)

    def test_validation_with_added_identical_file(self):
        files = self.create_files()
        self.generate_mets_xml()

        added = os.path.join(self.datadir, 'added.txt')
        with open(added, 'w') as f:
            with open(files[1]) as f1:
                f.write(f1.read())
        self.generate_premis_xml()

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        msg = '3 confirmed, 1 added, 0 changed, 0 renamed, 0 deleted$'
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.premis)

    def test_validation_with_all_alterations(self):
        files = self.create_files()
        self.generate_mets_xml()

        with open(files[0], 'a') as f:
            f.write('changed')
        os.remove(files[1])
        os.rename(files[2], os.path.join(self.datadir, 'new.txt'))
        added = os.path.join(self.datadir, 'added.txt')
        with open(added, 'w') as f:
            f.write('added')
        self.generate_premis_xml()

        self.validator = XMLComparisonValidator(context=self.mets, options=self.options)
        msg = '0 confirmed, 1 added, 1 changed, 1 renamed, 1 deleted$'
        with self.assertRaisesRegexp(ValidationError, msg):
            self.validator.validate(self.premis)
