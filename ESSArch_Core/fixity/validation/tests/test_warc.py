import os
import shutil
import tempfile
from unittest import mock

from click.testing import CliRunner
from django.test import TestCase

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.warc import WarcValidator


class WarcValidatorTests(TestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

    def test_valid(self):
        validator = WarcValidator()
        shutil.copy2(os.path.join(os.path.dirname(__file__), 'example.warc.gz'), self.datadir)
        validator.validate(os.path.join(self.datadir, 'example.warc.gz'))

        self.assertEqual(Validation.objects.count(), 1)
        self.assertEqual(Validation.objects.filter(passed=True).count(), 1)

    def test_wrong_chunks(self):
        validator = WarcValidator()
        shutil.copy2(os.path.join(os.path.dirname(__file__), 'example-wrong-chunks.warc.gz'), self.datadir)
        with self.assertRaises(ValidationError):
            validator.validate(os.path.join(self.datadir, 'example-wrong-chunks.warc.gz'))

    def test_bad_digest(self):
        validator = WarcValidator()
        shutil.copy2(os.path.join(os.path.dirname(__file__), 'example-bad-digest.warc'), self.datadir)
        with self.assertRaises(ValidationError):
            validator.validate(os.path.join(self.datadir, 'example-bad-digest.warc'))

    @mock.patch('ESSArch_Core.fixity.validation.backends.warc.WarcValidator.validate')
    def test_cli(self, mock_validate):
        runner = CliRunner()
        with runner.isolated_filesystem():
            open('foo.warc.gz', 'a').close()

            result = runner.invoke(WarcValidator.cli, ['foo.warc.gz'])
            mock_validate.assert_called_once_with('foo.warc.gz')

            self.assertEqual(result.exit_code, 0)
