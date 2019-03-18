import os
import shutil
import tempfile

from django.test import TestCase

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.fixed_width import FixedWidthValidator


class FixedWidthValidatorTests(TestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

    def create_file(self, data, filename, encoding='utf-8'):
        path = os.path.join(self.datadir, filename)
        with open(path, 'w', encoding=encoding) as f:
            f.write(data)

        return path

    def test_valid(self):
        test_file = self.create_file("""\
Bruce Wayne    Gotham City  2719380601
Clark Kent     Metropolis   1 19390301
""", 'foo.txt')

        fields = [
            {
                "name": "name",
                "datatype": "str",
                "start": 0,
                "end": 15,
                "length": 15,
            },
            {
                "name": "city",
                "datatype": "str",
                "start": 15,
                "end": 28,
                "length": 13,
            },
            {
                "name": "issue",
                "datatype": "int",
                "start": 28,
                "end": 30,
                "length": 2,
            },
            {
                "name": "published",
                "datatype": "date",
                "null": "19390301",
                "start": 30,
                "end": 38,
                "length": 8,
            }
        ]

        validator = FixedWidthValidator()
        validator.validate(test_file, expected=fields)

        self.assertFalse(Validation.objects.filter(passed=False).exists())

    def test_str_datatype_with_only_digits(self):
        test_file = self.create_file("""\
123
""", 'foo.txt')

        fields = [
            {
                "name": "namn",
                "datatype": "str",
                "start": 0,
                "end": 3,
                "length": 3
            },
        ]

        validator = FixedWidthValidator()
        validator.validate(test_file, expected=fields)

        self.assertFalse(Validation.objects.filter(passed=False).exists())

    def test_str_datatype_with_float(self):
        test_file = self.create_file("""\
123.456
""", 'foo.txt')

        fields = [
            {
                "name": "namn",
                "datatype": "str",
                "start": 0,
                "end": 7,
                "length": 7
            },
        ]

        validator = FixedWidthValidator()
        validator.validate(test_file, expected=fields)

        self.assertFalse(Validation.objects.filter(passed=False).exists())

    def test_custom_filler(self):
        test_file = self.create_file("""\
Bruce Wayne####Gotham City##2719380601
Clark Kent#####Metropolis###1#19390301
""", 'foo.txt')

        fields = [
            {
                "name": "name",
                "datatype": "str",
                "start": 0,
                "end": 15,
                "length": 15,
            },
            {
                "name": "city",
                "datatype": "str",
                "start": 15,
                "end": 28,
                "length": 13,
            },
            {
                "name": "issue",
                "datatype": "int",
                "start": 28,
                "end": 30,
                "length": 2,
            },
            {
                "name": "published",
                "datatype": "date",
                "null": "19390301",
                "start": 30,
                "end": 38,
                "length": 8,
            }
        ]

        validator = FixedWidthValidator(options={'filler': '#'})
        validator.validate(test_file, expected=fields)

        self.assertFalse(Validation.objects.filter(passed=False).exists())

    def test_invalid_line_length(self):
        test_file = self.create_file("""\
Bruce Wayne####Gotham City##2719380601
""", 'foo.txt')

        fields = [
            {
                "name": "name",
                "datatype": "str",
                "start": 0,
                "end": 15,
                "length": 15,
            },
            {
                "name": "city",
                "datatype": "str",
                "start": 15,
                "end": 28,
                "length": 13,
            },
            {
                "name": "issue",
                "datatype": "int",
                "start": 28,
                "end": 30,
                "length": 2,
            },
            {
                "name": "published",
                "datatype": "date",
                "null": "19390301",
                "start": 30,
                "end": 40,
                "length": 10,
            }
        ]

        validator = FixedWidthValidator()

        with self.assertRaises(ValidationError):
            validator.validate(test_file, expected=fields)

        self.assertEqual(Validation.objects.filter(passed=False).count(), 1)

    def test_conflicting_line_length(self):
        test_file = self.create_file("""\
foo
""", 'foo.txt')

        fields = [
            {
                "name": "namn",
                "datatype": "str",
                "start": 0,
                "end": 3,
                "length": 10
            },
        ]

        validator = FixedWidthValidator()

        with self.assertRaises(ValidationError):
            validator.validate(test_file, expected=fields)

        self.assertEqual(Validation.objects.filter(passed=False).count(), 2)

    def test_invalid_data_type(self):
        test_file = self.create_file("""\
abc
""", 'foo.txt')

        fields = [
            {
                "name": "date",
                "datatype": "int",
                "start": 0,
                "end": 3,
                "length": 3
            }
        ]

        validator = FixedWidthValidator()

        with self.assertRaises(ValidationError):
            validator.validate(test_file, expected=fields)

        self.assertEqual(Validation.objects.filter(passed=False).count(), 1)

        test_file = self.create_file("""\
abc
""", 'foo.txt')

        fields = [
            {
                "name": "date",
                "datatype": "float",
                "start": 0,
                "end": 3,
                "length": 3
            }
        ]

        validator = FixedWidthValidator()

        with self.assertRaises(ValidationError):
            validator.validate(test_file, expected=fields)

        self.assertEqual(Validation.objects.filter(passed=False).count(), 2)

    def test_invalid_date_format(self):
        test_file = self.create_file("""\
12345678
""", 'foo.txt')

        fields = [
            {
                "name": "date",
                "datatype": "date",
                "null": "99991231",
                "start": 0,
                "end": 8,
                "length": 8
            }
        ]

        validator = FixedWidthValidator()

        with self.assertRaises(ValidationError):
            validator.validate(test_file, expected=fields)

        self.assertEqual(Validation.objects.filter(passed=False).count(), 1)

    def test_custom_encoding(self):
        test_file = self.create_file("""\
åäö
""", 'foo.txt', encoding='windows-1252')

        fields = [
            {
                "name": "name",
                "datatype": "str",
                "start": 0,
                "end": 3,
                "length": 3
            }
        ]

        validator = FixedWidthValidator(options={'encoding': 'windows-1252'})
        validator.validate(test_file, expected=fields)

        self.assertFalse(Validation.objects.filter(passed=False).exists())

    def test_invalid_encoding(self):
        test_file = self.create_file("""\
åäö
""", 'foo.txt', encoding='windows-1252')

        fields = [
            {
                "name": "name",
                "datatype": "str",
                "start": 0,
                "end": 3,
                "length": 3
            }
        ]

        validator = FixedWidthValidator(options={'encoding': 'cp950'})

        with self.assertRaises(ValidationError):
            validator.validate(test_file, expected=fields)

        self.assertEqual(Validation.objects.filter(passed=False).count(), 1)
