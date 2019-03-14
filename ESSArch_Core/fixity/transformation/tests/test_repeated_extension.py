from unittest import mock

from django.test import TestCase

from ESSArch_Core.fixity.transformation.backends.repeated_extension import RepeatedExtensionTransformer


@mock.patch("ESSArch_Core.fixity.transformation.backends.repeated_extension.os.rename")
class RepeatedExtensionTransformerTests(TestCase):
    def test_valid(self, mock_rename):
        RepeatedExtensionTransformer().transform('foo.xml')
        mock_rename.assert_called_once_with('foo.xml', 'foo.xml')

    def test_valid_multiple(self, mock_rename):
        RepeatedExtensionTransformer().transform('foo.tar.gz')
        mock_rename.assert_called_once_with('foo.tar.gz', 'foo.tar.gz')

    def test_valid_extension_match_name(self, mock_rename):
        RepeatedExtensionTransformer().transform('foo.foo')
        mock_rename.assert_called_once_with('foo.foo', 'foo.foo')

    def test_valid_repeated_extension_name(self, mock_rename):
        RepeatedExtensionTransformer().transform('foo.pdfpdf')
        mock_rename.assert_called_once_with('foo.pdfpdf', 'foo.pdfpdf')

    def test_valid_every_other_repeated(self, mock_rename):
        RepeatedExtensionTransformer().transform('foo.tar.gz.tar.gz')
        mock_rename.assert_called_once_with('foo.tar.gz.tar.gz', 'foo.tar.gz.tar.gz')

    def test_invalid(self, mock_rename):
        RepeatedExtensionTransformer().transform('foo.xml.xml')
        mock_rename.assert_called_once_with('foo.xml.xml', 'foo.xml')

    def test_invalid_with_more_than_two(self, mock_rename):
        RepeatedExtensionTransformer().transform('foo.xml.xml.xml.xml.xml')
        mock_rename.assert_called_once_with('foo.xml.xml.xml.xml.xml', 'foo.xml')

    def test_invalid_in_middle_of_extensions(self, mock_rename):
        RepeatedExtensionTransformer().transform('foo.tar.xml.xml.gz')
        mock_rename.assert_called_once_with('foo.tar.xml.xml.gz', 'foo.tar.xml.gz')
