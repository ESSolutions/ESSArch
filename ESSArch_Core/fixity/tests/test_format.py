from unittest import mock
from django.test import TestCase

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.fixity.format import FormatIdentifier, DEFAULT_MIMETYPE
from ESSArch_Core.exceptions import FileFormatNotAllowed


class FormatIdentifierMimeTypeTests(TestCase):
    @mock.patch("ESSArch_Core.fixity.format.mimetypes.init")
    def test_default_list(self, mock_mimetypes_init):
        fid = FormatIdentifier(allow_unknown_file_types=True)
        fid._init_mimetypes()
        mock_mimetypes_init.assert_called_once_with()

    @mock.patch(
        "ESSArch_Core.fixity.format.mimetypes.guess_type",
        return_value=('application/x-tar', 'gzip'))
    def test_gzipped_file(self, mock_mimetypes_init):
        fid = FormatIdentifier(allow_unknown_file_types=True)
        self.assertEqual(fid.get_mimetype('foo.tar.gz'), 'application/gzip')

    @mock.patch("ESSArch_Core.fixity.format.mimetypes.guess_type", return_value=(None, mock.ANY))
    def test_unknown_content_type(self, mock_mimetypes_init):
        fid = FormatIdentifier(allow_unknown_file_types=True)
        self.assertEqual(fid.get_mimetype('some_random_file'), DEFAULT_MIMETYPE)

    @mock.patch("ESSArch_Core.fixity.format.mimetypes.guess_type", return_value=(None, mock.ANY))
    def test_unknown_content_type_when_not_allowed_should_raise_exception(self, mock_mimetypes_init):
        fid = FormatIdentifier(allow_unknown_file_types=False)
        with self.assertRaises(FileFormatNotAllowed):
            fid.get_mimetype('some_random_file')

    @mock.patch("ESSArch_Core.fixity.format.os.path.isfile", return_value=True)
    @mock.patch("ESSArch_Core.fixity.format.mimetypes.init")
    def test_custom_list(self, mock_mimetypes_init, isfile):
        mimetypes_file = Path.objects.create(
            entity="path_mimetypes_definitionfile", value='path/to/mime.types')
        fid = FormatIdentifier(allow_unknown_file_types=True)
        fid._init_mimetypes()
        mock_mimetypes_init.assert_called_once_with(
            files=[mimetypes_file.value])

    @mock.patch("ESSArch_Core.fixity.format.os.path.isfile", return_value=False)
    @mock.patch("ESSArch_Core.fixity.format.mimetypes.init")
    def test_custom_list_missing_file(self, mock_mimetypes_init, isfile):
        Path.objects.create(entity="path_mimetypes_definitionfile", value='path/to/mime.types')
        fid = FormatIdentifier(allow_unknown_file_types=True)
        fid._init_mimetypes()
        mock_mimetypes_init.assert_called_once_with()

    @mock.patch("ESSArch_Core.fixity.format.mimetypes.guess_type", return_value=(None, mock.ANY))
    def test_handle_matches_when_no_matches(self, mock_mimetypes_init):
        fid = FormatIdentifier(allow_unknown_file_types=True)
        fid.handle_matches('fullname', [], mock.ANY)

        self.assertEqual(fid.format_name, 'Unknown File Format')
        self.assertEqual(fid.format_version, None)
        self.assertEqual(fid.format_registry_key, None)

    @mock.patch("ESSArch_Core.fixity.format.mimetypes.guess_type", return_value=(None, mock.ANY))
    def test_handle_matches_when_no_matches_and_unknown_types_not_allowed(self, mock_mimetypes_init):
        fid = FormatIdentifier(allow_unknown_file_types=False)

        with self.assertRaises(ValueError):
            fid.handle_matches('fullname', [], mock.ANY)

    @mock.patch("ESSArch_Core.fixity.format.mimetypes.guess_type", return_value=(None, mock.ANY))
    def test_handle_matches_when_no_match_on_name_or_version_or_reg_key(self, mock_mimetypes_init):
        fid = FormatIdentifier(allow_unknown_file_types=True)
        dummy_matches = [('a', 'b'), ('c', 'd')]

        fid.handle_matches('fullname', dummy_matches, mock.ANY)

        self.assertEqual(fid.format_name, None)
        self.assertEqual(fid.format_version, None)
        self.assertEqual(fid.format_registry_key, None)
