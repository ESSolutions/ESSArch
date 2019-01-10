from unittest import mock
from django.test import TestCase

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.fixity.format import FormatIdentifier


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
        mimetypes_file = Path.objects.create(
            entity="path_mimetypes_definitionfile", value='path/to/mime.types')
        fid = FormatIdentifier(allow_unknown_file_types=True)
        fid._init_mimetypes()
        mock_mimetypes_init.assert_called_once_with()
