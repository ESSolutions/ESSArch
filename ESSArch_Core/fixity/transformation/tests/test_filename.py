import string
from unittest import mock

from django.test import TestCase

from ESSArch_Core.fixity.transformation.backends.filename import FilenameTransformer


class FilenameTransformerCleanTests(TestCase):
    def test_default_correct(self):
        self.assertEqual(FilenameTransformer.clean('foo.xml'), 'foo.xml')

    def test_default_replace_swedish_characters(self):
        self.assertEqual(FilenameTransformer.clean('åäö.xml'), 'aao.xml')

    def test_default_replace_whitespace(self):
        self.assertEqual(FilenameTransformer.clean('f o o.xml'), 'f_o_o.xml')

    def test_default_remove_special_characters(self):
        self.assertEqual(FilenameTransformer.clean('$f?o!o).x%m#l+'), 'foo.xml')

    def test_custom_replace(self):
        replace = {
            '0': 'o',
            ' ': '_',
            ':': '_',
        }

        self.assertEqual(FilenameTransformer.clean('f:0o.  xml', replace=replace), 'f_oo.__xml')

    def test_custom_whitelist(self):
        whitelist = '.4{}'.format(string.ascii_letters)
        self.assertEqual(FilenameTransformer.clean('f1o2o3.x4m5l6', whitelist=whitelist), 'foo.x4ml')

    def test_without_unicode_normalization(self):
        self.assertEqual(FilenameTransformer.clean('fåoäoö.xml', normalize_unicode=False), 'foo.xml')


@mock.patch("ESSArch_Core.fixity.transformation.backends.filename.os.rename")
class FilenameTransformerTransformTests(TestCase):
    def test_transform_invalid(self, mock_rename):
        FilenameTransformer().transform('åäö.xml')
        mock_rename.assert_called_once_with('åäö.xml', 'aao.xml')

    def test_transform_valid(self, mock_rename):
        FilenameTransformer().transform('foo.xml')
        mock_rename.assert_called_once_with('foo.xml', 'foo.xml')
