from django.test import TestCase

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.repeated_extension import RepeatedExtensionValidator


class RepeatedExtensionValidatorTests(TestCase):
    def test_valid(self):
        validator = RepeatedExtensionValidator()
        validator.validate('foo.xml')

        self.assertEqual(Validation.objects.count(), 1)
        self.assertEqual(Validation.objects.filter(passed=True).count(), 1)

    def test_valid_multiple(self):
        validator = RepeatedExtensionValidator()
        validator.validate('foo.tar.gz')

        self.assertEqual(Validation.objects.count(), 1)
        self.assertEqual(Validation.objects.filter(passed=True).count(), 1)

    def test_valid_extension_match_name(self):
        validator = RepeatedExtensionValidator()
        validator.validate('foo.foo')

        self.assertEqual(Validation.objects.count(), 1)
        self.assertEqual(Validation.objects.filter(passed=True).count(), 1)

    def test_valid_repeated_extension_name(self):
        validator = RepeatedExtensionValidator()
        validator.validate('foo.pdfpdf')

        self.assertEqual(Validation.objects.count(), 1)
        self.assertEqual(Validation.objects.filter(passed=True).count(), 1)

    def test_valid_every_other_repeated(self):
        validator = RepeatedExtensionValidator()
        validator.validate('foo.tar.gz.tar.gz')

        self.assertEqual(Validation.objects.count(), 1)
        self.assertEqual(Validation.objects.filter(passed=True).count(), 1)

    def test_invalid(self):
        validator = RepeatedExtensionValidator()
        with self.assertRaises(ValidationError):
            validator.validate('foo.xml.xml')

        self.assertEqual(Validation.objects.count(), 1)
        self.assertEqual(Validation.objects.filter(passed=False).count(), 1)

    def test_invalid_with_more_than_two(self):
        validator = RepeatedExtensionValidator()
        with self.assertRaises(ValidationError):
            validator.validate('foo.xml.xml.xml.xml.xml')

        self.assertEqual(Validation.objects.count(), 1)
        self.assertEqual(Validation.objects.filter(passed=False).count(), 1)

    def test_invalid_in_middle_of_extensions(self):
        validator = RepeatedExtensionValidator()
        with self.assertRaises(ValidationError):
            validator.validate('foo.tar.xml.xml.gz')

        self.assertEqual(Validation.objects.count(), 1)
        self.assertEqual(Validation.objects.filter(passed=False).count(), 1)
