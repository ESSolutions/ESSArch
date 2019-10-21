from click.testing import CliRunner
from django.test import SimpleTestCase

from ESSArch_Core.cli.commands.convert import convert


class ConversionCommandTest(SimpleTestCase):
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(convert, ['--help'])
        self.assertEqual(result.exit_code, 0)
