from unittest import mock

from click.testing import CliRunner
from django.test import TestCase

from ESSArch_Core.fixity.conversion.backends.image import ImageConverter


class ImageConverterTests(TestCase):
    @mock.patch('ESSArch_Core.fixity.conversion.backends.image.ImageConverter.convert')
    def test_cli(self, mock_convert):
        runner = CliRunner()
        with runner.isolated_filesystem():
            open('foo.jpg', 'a')

            result = runner.invoke(ImageConverter.cli, [
                'foo.jpg', 'foo.png',
                '--in-fmt', 'image/jpeg',
                '--out-fmt', 'image/png',
            ])
            mock_convert.assert_called_once_with(
                'foo.jpg', 'foo.png',
                'image/jpeg', 'image/png',
            )

            self.assertEqual(result.exit_code, 0)
