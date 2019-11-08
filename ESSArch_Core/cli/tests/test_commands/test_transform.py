from click.testing import CliRunner
from django.test import SimpleTestCase

from ESSArch_Core.cli.commands.transform import transform


class TransformCommandTest(SimpleTestCase):
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(transform, ['--help'])
        self.assertEqual(result.exit_code, 0)
