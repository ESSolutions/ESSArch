from django.test import TestCase

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.filename import FilenameValidator


class FilenameValidatorTests(TestCase):
    def test_valid(self):
        validator = FilenameValidator()
        validator.validate('foo.xml')

        self.assertTrue(Validation.objects.count(), 1)
        self.assertTrue(Validation.objects.filter(passed=True).count(), 1)

    def test_invalid(self):
        validator = FilenameValidator()
        with self.assertRaises(ValidationError):
            validator.validate('foo?.xml')

        self.assertTrue(Validation.objects.count(), 1)
        self.assertTrue(Validation.objects.filter(passed=False).count(), 1)

    def test_custom_pattern(self):
        validator = FilenameValidator()
        pattern = r'^[a-z]+\?\.[a-z]+$'

        validator.validate('foo?.xml', pattern)

        self.assertTrue(Validation.objects.count(), 1)
        self.assertTrue(Validation.objects.filter(passed=True).count(), 1)

        with self.assertRaises(ValidationError):
            validator.validate('foo!.xml', pattern)

        self.assertTrue(Validation.objects.count(), 2)
        self.assertTrue(Validation.objects.filter(passed=True).count(), 1)
        self.assertTrue(Validation.objects.filter(passed=False).count(), 1)
