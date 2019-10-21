import os

from click.testing import CliRunner
from django.test import SimpleTestCase

from ESSArch_Core.cli.commands.settings import generate


class SettingsCommandTest(SimpleTestCase):
    def test_generate_new_file(self):
        runner = CliRunner()
        path = 'local_test_settings.py'

        with runner.isolated_filesystem():
            result = runner.invoke(generate, ['-p', path])

            self.assertTrue(os.path.isfile(path))
            self.assertEqual(result.exit_code, 0)

    def test_generate_existing_file_overwrite(self):
        runner = CliRunner()
        path = 'local_test_settings.py'

        with runner.isolated_filesystem():
            with open(path, 'w') as f:
                f.write('foo')

            result = runner.invoke(generate, ['-p', path, '--overwrite'])

            self.assertTrue(os.path.isfile(path))
            self.assertEqual(result.exit_code, 0)
            self.assertNotEqual(open(path).read(), 'foo')

    def test_generate_existing_file_no_overwrite(self):
        runner = CliRunner()
        path = 'local_test_settings.py'

        with runner.isolated_filesystem():
            with open(path, 'w') as f:
                f.write('foo')

            result = runner.invoke(generate, ['-p', path, '--no-overwrite'])

            self.assertTrue(os.path.isfile(path))
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(open(path).read(), 'foo')
