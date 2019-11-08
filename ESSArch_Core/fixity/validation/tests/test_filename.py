import shutil
import tempfile

from django.test import TestCase

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.filename import FilenameValidator


class FilenameValidatorTests(TestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

    def test_valid(self):
        with tempfile.NamedTemporaryFile(dir=self.datadir, suffix='.pdf') as f:
            validator = FilenameValidator()
            validator.validate(f.name)

        self.assertEqual(Validation.objects.count(), 1)
        self.assertEqual(Validation.objects.filter(passed=True).count(), 1)

    def test_valid_directory(self):
        with tempfile.TemporaryDirectory(dir=self.datadir) as f:
            validator = FilenameValidator()
            validator.validate(f)

        self.assertEqual(Validation.objects.count(), 1)
        self.assertEqual(Validation.objects.filter(passed=True).count(), 1)

    def test_invalid(self):
        validator = FilenameValidator()
        with tempfile.NamedTemporaryFile(dir=self.datadir, suffix='#.pdf') as f:
            validator = FilenameValidator()
            with self.assertRaises(ValidationError):
                validator.validate(f.name)

        self.assertEqual(Validation.objects.count(), 1)
        self.assertEqual(Validation.objects.filter(passed=False).count(), 1)

    def test_invalid_directory(self):
        with tempfile.TemporaryDirectory(dir=self.datadir, suffix='.pdf') as f:
            validator = FilenameValidator()
            with self.assertRaises(ValidationError):
                validator.validate(f)

        self.assertEqual(Validation.objects.count(), 1)
        self.assertEqual(Validation.objects.filter(passed=False).count(), 1)

    def test_custom_pattern(self):
        validator = FilenameValidator()
        pattern = r'^[a-z]+\?\.[a-z]+$'

        validator.validate('foo?.xml', pattern)

        self.assertEqual(Validation.objects.count(), 1)
        self.assertEqual(Validation.objects.filter(passed=True).count(), 1)

        with self.assertRaises(ValidationError):
            validator.validate('foo!.xml', pattern)

        self.assertEqual(Validation.objects.count(), 2)
        self.assertEqual(Validation.objects.filter(passed=True).count(), 1)
        self.assertEqual(Validation.objects.filter(passed=False).count(), 1)
