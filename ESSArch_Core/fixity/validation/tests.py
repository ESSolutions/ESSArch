import errno
import hashlib
import os

from django.test import SimpleTestCase

from pyfakefs import fake_filesystem_unittest

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.validation.backends.checksum import ChecksumValidator

class ChecksumValidatorTests(fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.test_file = 'foo.txt'
        self.content = 'test file'
        with open(self.test_file, 'wb') as f:
            f.write(self.content)

        md5 = hashlib.md5(self.content)
        self.checksum = md5.hexdigest()

    def tearDown(self):
        pass

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
        self.test_file = 'foo.txt'
        self.xml_file = 'files.xml'

        self.content = 'test file'
        with open(self.test_file, 'wb') as f:
            f.write(self.content)

        md5 = hashlib.md5(self.content)
        self.checksum = md5.hexdigest()

    def tearDown(self):
        files = [self.test_file, self.xml_file]

        for f in files:
            try:
                os.remove(f)
            except OSError as exc:
                if exc.errno != errno.ENOENT:
                    raise

    def test_validate_against_xml_file_valid(self):
        xml_str = '<root><file CHECKSUM="{hash}" CHECKSUMTYPE="{alg}"><FLocat href="{file}"/></file></root>'.format(
            hash=self.checksum, alg='md5', file=self.test_file)

        with open(self.xml_file, 'wb') as f:
            f.write(xml_str)

        self.assertTrue(os.path.isfile(self.xml_file))

        options = {'expected': self.xml_file, 'algorithm': 'md5'}
        self.validator = ChecksumValidator(context='xml_file', options=options)
        self.validator.validate(self.test_file)

    def test_validate_against_xml_file_invalid(self):
        xml_str = '<root><file CHECKSUM="{hash}" CHECKSUMTYPE="{alg}"><FLocat href="{file}"/></file></root>'.format(
            hash=self.checksum + 'appended', alg='md5', file=self.test_file)

        with open(self.xml_file, 'wb') as f:
            f.write(xml_str)

        options = {'expected': self.xml_file, 'algorithm': 'md5'}
        self.validator = ChecksumValidator(context='xml_file', options=options)

        with self.assertRaises(ValidationError):
            self.validator.validate(self.test_file)

    def test_validate_against_xml_file_with_multiple_files(self):
        test_file2 = 'bar.txt'
        content2 = 'test file 2'
        with open(test_file2, 'wb') as f:
            f.write(content2)

        md5 = hashlib.md5(content2)
        checksum2 = md5.hexdigest()

        xml_str = '''
            <root>
                <file CHECKSUM="{hash}" CHECKSUMTYPE="{alg}">
                    <FLocat href="{file}"/>
                </file>
                <file CHECKSUM="{hash2}" CHECKSUMTYPE="{alg}">
                    <FLocat href="{file2}"/>
                </file>
            </root>'''.format(
                    hash=self.checksum, alg='md5', file=self.test_file,
                    hash2=checksum2, file2=test_file2)

        with open(self.xml_file, 'wb') as f:
            f.write(xml_str)

        self.assertTrue(os.path.isfile(self.xml_file))

        options = {'expected': self.xml_file, 'algorithm': 'md5'}
        self.validator = ChecksumValidator(context='xml_file', options=options)

        self.validator.validate(self.test_file)
        self.validator.validate(test_file2)
