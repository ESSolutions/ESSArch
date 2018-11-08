import os
import shutil
import tempfile

import mock
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.fixity.format import FormatIdentifier
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.util import timestamp_to_datetime


class FormatIdentifierMimeTypeTests(TestCase):
    def test_default_list(self):
        fid = FormatIdentifier(allow_unknown_file_types=True)
        self.assertEqual(fid.get_mimetype('foo.txt'), 'text/plain')
        self.assertEqual(fid.get_mimetype('foo.zxc'), 'application/octet-stream')

    def test_gzipped_file(self):
        fid = FormatIdentifier(allow_unknown_file_types=True)
        self.assertEqual(fid.get_mimetype('foo.tar.gz'), 'application/gzip')

    def test_custom_list(self):
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(b'text/plain zxc')
        f.seek(0)
        f.close()
        path = f.name
        mimetypes_file = Path.objects.create(entity="path_mimetypes_definitionfile", value=path)
        fid = FormatIdentifier(allow_unknown_file_types=True)
        self.assertEqual(fid.get_mimetype('foo.zxc'), 'text/plain')
        self.assertEqual(fid.get_mimetype('foo.txt'), 'application/octet-stream')
