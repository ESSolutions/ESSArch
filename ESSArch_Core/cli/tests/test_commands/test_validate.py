from click.testing import CliRunner
from django.test import SimpleTestCase

from ESSArch_Core.cli.commands.validate import validate


class ValidateCommandTest(SimpleTestCase):
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(validate, ['--help'])
        self.assertEqual(result.exit_code, 0)
