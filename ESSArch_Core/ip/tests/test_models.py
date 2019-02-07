import os
import shutil
import tempfile
import uuid

from unittest import mock
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.util import normalize_path, timestamp_to_datetime


class InformationPackageListFilesTests(TestCase):
    def setUp(self):
        self.datadir = normalize_path(tempfile.mkdtemp())
        self.ip = InformationPackage.objects.create(object_path=self.datadir)

        self.addCleanup(shutil.rmtree, self.datadir)

    def test_list_file(self):
        fd, path = tempfile.mkstemp(dir=self.datadir)
        os.close(fd)
        self.assertEqual(
            self.ip.list_files(),
            [{
                'type': 'file',
                'name': os.path.basename(path),
                'size': 0,
                'modified': timestamp_to_datetime(os.stat(path).st_mtime)
            }]
        )

    def test_list_folder(self):
        path = tempfile.mkdtemp(dir=self.datadir)
        self.assertEqual(
            self.ip.list_files(),
            [{
                'type': 'dir',
                'name': os.path.basename(path),
                'size': 0,
                'modified': timestamp_to_datetime(os.stat(path).st_mtime)
            }]
        )

    def test_list_folder_content(self):
        path = tempfile.mkdtemp(dir=self.datadir)
        fd, filepath = tempfile.mkstemp(dir=path)
        os.close(fd)
        self.assertEqual(
            self.ip.list_files(path=path),
            [{
                'type': 'file',
                'name': os.path.basename(filepath),
                'size': os.stat(filepath).st_size,
                'modified': timestamp_to_datetime(os.stat(filepath).st_mtime)
            }]
        )


class GetPathResponseTests(TestCase):
    def setUp(self):
        self.datadir = normalize_path(tempfile.mkdtemp())
        self.ip = InformationPackage.objects.create(object_path=self.datadir)
        self.request = APIRequestFactory()

        self.addCleanup(shutil.rmtree, self.datadir)

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.open_file')
    @mock.patch('ESSArch_Core.ip.models.generate_file_response')
    @mock.patch('ESSArch_Core.ip.models.FormatIdentifier')
    def test_get_file(self, mock_fid, mock_gen_file_resp, mock_open_file):
        fd, path = tempfile.mkstemp(dir=self.datadir)
        os.close(fd)
        relpath = os.path.relpath(path, self.datadir)

        response = self.ip.get_path_response(relpath, self.request)
        response.close()

        mocked_file = mock_open_file.return_value
        mocked_mimetype = mock_fid.return_value.get_mimetype.return_value
        mock_gen_file_resp.assert_called_once_with(mocked_file, mocked_mimetype, force_download=False, name=relpath)

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.list_files')
    @mock.patch('ESSArch_Core.ip.models.FormatIdentifier')
    def test_get_folder(self, mock_fid, mock_list_files):
        path = tempfile.mkdtemp(dir=self.datadir)

        relpath = os.path.basename(path)
        response = self.ip.get_path_response(relpath, self.request)
        response.close()
        mock_list_files.assert_called_once_with(relpath)

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.open_file')
    @mock.patch('ESSArch_Core.ip.models.generate_file_response')
    @mock.patch('ESSArch_Core.ip.models.FormatIdentifier')
    def test_get_file_in_folder(self, mock_fid, mock_gen_file_resp, mock_open_file):
        path = tempfile.mkdtemp(dir=self.datadir)
        fd, filepath = tempfile.mkstemp(dir=path)
        os.close(fd)
        relpath = os.path.relpath(filepath, self.datadir)

        response = self.ip.get_path_response(os.path.relpath(filepath, self.datadir), self.request)
        response.close()

        mocked_file = mock_open_file.return_value
        mocked_mimetype = mock_fid.return_value.get_mimetype.return_value
        mock_gen_file_resp.assert_called_once_with(mocked_file, mocked_mimetype, force_download=False, name=relpath)


class GetPathResponseContainerTests(TestCase):
    def setUp(self):
        self.file = tempfile.NamedTemporaryFile(delete=False)
        self.file.close()
        self.file = normalize_path(self.file.name)
        self.ip = InformationPackage.objects.create(object_path=self.file)
        self.request = APIRequestFactory()

        self.addCleanup(os.remove, self.file)

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.open_file')
    @mock.patch('ESSArch_Core.ip.models.InformationPackage.list_files')
    @mock.patch('ESSArch_Core.ip.models.FormatIdentifier')
    def test_list_files_in_ip_container(self, mock_fid, mock_list_files, mock_open_file):
        path = os.path.basename(self.file)
        response = self.ip.get_path_response(path, self.request)
        response.close()

        mock_open_file.return_value
        mock_fid.return_value.get_mimetype.return_value
        mock_list_files.assert_called_once_with(path)


class StatusTest(TestCase):

    def setUp(self):
        self.datadir = normalize_path(tempfile.mkdtemp())
        self.ip = InformationPackage.objects.create(object_path=self.datadir)

        self.addCleanup(shutil.rmtree, self.datadir)

    def test_status_is_100_when_state_is_any_completed_state(self):
        completed_states = ["Prepared", "Uploaded", "Created", "Submitted", "Received", "Transferred", 'Archived']

        for state in completed_states:
            self.ip.state = state
            self.assertEqual(self.ip.status(), 100)

    def test_status_is_33_when_state_is_preparing_and_submission_agreement_is_not_locked(self):
        self.ip.state = 'Preparing'
        self.ip.submission_agreement_locked = False

        self.assertEqual(self.ip.status(), 33)

    def test_status_is_between_66_and_100_when_state_is_preparing_and_submission_agreement_is_locked(self):
        self.ip.state = 'Preparing'
        self.ip.submission_agreement_locked = True

        status = self.ip.status()
        self.assertGreaterEqual(status, 66)
        self.assertLessEqual(status, 100)

    def test_status_is_100_if_state_is_None(self):
        self.ip.state = None

        self.assertEqual(self.ip.status(), 100)

    def test_status_is_100_if_state_is_an_unhandled_type(self):
        self.ip.state = uuid.uuid4

        self.assertEqual(self.ip.status(), 100)
