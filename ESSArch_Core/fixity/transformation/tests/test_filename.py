import os
import shutil
import string
import tempfile
from unittest import mock

from click.testing import CliRunner
from django.test import TestCase

from ESSArch_Core.fixity.transformation.backends.filename import (
    DEFAULT_WHITELIST_FILE,
    FilenameTransformer,
)


class FilenameTransformerCleanTests(TestCase):
    def test_default_correct(self):
        whitelist = DEFAULT_WHITELIST_FILE
        self.assertEqual(FilenameTransformer.clean('foo.xml', whitelist), 'foo.xml')

    def test_default_replace_swedish_characters(self):
        whitelist = DEFAULT_WHITELIST_FILE
        self.assertEqual(FilenameTransformer.clean('åäö.xml', whitelist), 'aao.xml')

    def test_replace_whitespace(self):
        whitelist = DEFAULT_WHITELIST_FILE
        replace = {
            ' ': '_',
        }

        self.assertEqual(FilenameTransformer.clean('f o o.xml', whitelist, replace), 'f_o_o.xml')

    def test_default_remove_special_characters(self):
        whitelist = DEFAULT_WHITELIST_FILE
        self.assertEqual(FilenameTransformer.clean('$f?o!o).x%m#l+', whitelist), 'foo.xml')

    def test_custom_replace(self):
        replace = {
            '0': 'o',
            ' ': '_',
            ':': '_',
        }

        whitelist = DEFAULT_WHITELIST_FILE
        self.assertEqual(FilenameTransformer.clean('f:0o.  xml', whitelist, replace=replace), 'f_oo.__xml')

    def test_custom_whitelist(self):
        whitelist = '.4{}'.format(string.ascii_letters)
        self.assertEqual(FilenameTransformer.clean('f1o2o3.x4m5l6', whitelist=whitelist), 'foo.x4ml')

    def test_without_unicode_normalization(self):
        whitelist = DEFAULT_WHITELIST_FILE
        self.assertEqual(FilenameTransformer.clean('fåoäoö.xml', whitelist, normalize_unicode=False), 'foo.xml')


@mock.patch("ESSArch_Core.fixity.transformation.backends.filename.os.rename")
class FilenameTransformerTransformTests(TestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

    def test_transform_invalid(self, mock_rename):
        sub_dir = os.path.join(self.datadir, 'åäö')
        path = os.path.join(sub_dir, 'åäö.xml')
        os.mkdir(sub_dir)
        open(path, 'a')

        FilenameTransformer().transform(path)
        mock_rename.assert_called_once_with(path, os.path.join(sub_dir, 'aao.xml'))

    def test_transform_valid(self, mock_rename):
        sub_dir = os.path.join(self.datadir, 'abc')
        path = os.path.join(sub_dir, 'foo.xml')
        os.mkdir(sub_dir)
        open(path, 'a')

        FilenameTransformer().transform(path)
        mock_rename.assert_called_once_with(path, path)

    def test_transform_invalid_directory(self, mock_rename):
        path = os.path.join(self.datadir, 'abc.xml')
        os.mkdir(path)

        FilenameTransformer().transform(path)
        mock_rename.assert_called_once_with(path, os.path.join(self.datadir, 'abc_xml'))

    def test_transform_custom_whitelist(self, mock_rename):
        path = 'foo.xml'
        whitelist = string.ascii_letters
        FilenameTransformer().transform(path, whitelist)

        mock_rename.assert_called_once_with(path, 'fooxml')

    def test_transform_custom_replace(self, mock_rename):
        path = 'foo.xml'
        replace = {'.': '_'}
        FilenameTransformer().transform(path, replace=replace)
        mock_rename.assert_called_once_with(path, 'foo_xml')


@mock.patch('ESSArch_Core.fixity.transformation.backends.filename.FilenameTransformer.transform')
class FilenameTransformerCliTests(TestCase):
    def test_cli(self, mock_transform):
        runner = CliRunner()
        with runner.isolated_filesystem():
            open('foo#.txt', 'a')
            whitelist = ".%s" % (string.ascii_letters)

            result = runner.invoke(FilenameTransformer.cli, [
                'foo#.txt',
                '--whitelist', whitelist,
                '--replace', '#', '_',
            ])
            mock_transform.assert_called_once_with('foo#.txt', whitelist, {'#': '_'}, True)

            self.assertEqual(result.exit_code, 0)
