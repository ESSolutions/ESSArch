from unittest import mock

from click.testing import CliRunner
from django.test import TestCase

from ESSArch_Core.fixity.conversion.backends.openssl import OpenSSLConverter


class OpenSSLConverterTests(TestCase):
    @mock.patch('ESSArch_Core.fixity.conversion.backends.openssl.OpenSSLConverter.convert')
    def test_cli(self, mock_convert):
        runner = CliRunner()
        with runner.isolated_filesystem():
            open('foo.pem', 'a')
            open('cert.pem', 'a')
            open('key.pem', 'a')

            result = runner.invoke(OpenSSLConverter.cli, [
                'foo.pem', 'foo.p7',
                '--in-fmt', 'application/x-pem-file',
                '--out-fmt', 'application/x-pkcs7-certificates',
                '--cert-file', 'cert.pem',
                '--in-key', 'key.pem',
                '--password', 'qwerty',
            ])
            mock_convert.assert_called_once_with(
                'foo.pem', 'foo.p7',
                'application/x-pem-file', 'application/x-pkcs7-certificates',
                ('cert.pem',), 'key.pem', 'qwerty'
            )

            self.assertEqual(result.exit_code, 0)
