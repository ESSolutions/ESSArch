import os
import shutil
import tempfile

from django.test import TestCase

from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.util import timestamp_to_datetime


class InformationPackageListFilesTests(TestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.ip = InformationPackage.objects.create(object_path=self.datadir)

        self.addCleanup(shutil.rmtree, self.datadir)

    def test_list_file(self):
        _, path = tempfile.mkstemp(dir=self.datadir)
        self.assertEqual(self.ip.list_files(), [{'type': 'file', 'name': os.path.basename(path), 'size': 0, 'modified': timestamp_to_datetime(os.stat(path).st_mtime)}])

    def test_list_folder(self):
        path = tempfile.mkdtemp(dir=self.datadir)
        self.assertEqual(self.ip.list_files(), [{'type': 'dir', 'name': os.path.basename(path), 'size': 0, 'modified': timestamp_to_datetime(os.stat(path).st_mtime)}])

    def test_list_folder_content(self):
        path = tempfile.mkdtemp(dir=self.datadir)
        _, filepath = tempfile.mkstemp(dir=path)
        self.assertEqual(self.ip.list_files(path=path), [{'type': 'file', 'name': os.path.basename(filepath), 'size': os.stat(filepath).st_size, 'modified': timestamp_to_datetime(os.stat(filepath).st_mtime)}])


