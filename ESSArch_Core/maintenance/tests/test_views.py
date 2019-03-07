import os
import shutil
import tempfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.maintenance.models import AppraisalJob, ConversionJob
from ESSArch_Core.maintenance.views import find_all_files
from ESSArch_Core.util import win_to_posix, normalize_path

User = get_user_model()


class CreateAppraisalRuleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.url = reverse('appraisalrule-list')

    def test_unauthenticated(self):
        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_with_permission(self):
        perm = Permission.objects.get(codename='add_appraisalrule')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ConversionJobViewSetPreviewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.conversion_job = ConversionJob.objects.create()
        self.url = reverse('conversionjob-preview', args=(self.conversion_job.pk,))

    def test_unauthenticated(self):
        response = self.client.get(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch('ESSArch_Core.maintenance.views.get_conversion_job_preview_files')
    def test_authenticated(self, mock_get_conversion_job_preview_files):
        mock_get_conversion_job_preview_files.return_value = ["file1", "file2"]
        self.client.force_authenticate(user=self.user)

        self.client.get(self.url, {'name': 'foo'})

        mock_get_conversion_job_preview_files.assert_called_once()


class AppraisalJobViewSetPreviewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.apprisal_job = AppraisalJob.objects.create()
        self.url = reverse('appraisaljob-preview', args=(self.apprisal_job.pk,))

    def test_unauthenticated(self):
        response = self.client.get(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch('ESSArch_Core.maintenance.views.get_appraisal_job_preview_files')
    def test_authenticated(self, mock_get_appraisal_job_preview_files):
        mock_get_appraisal_job_preview_files.return_value = ["file1", "file2"]
        self.client.force_authenticate(user=self.user)

        self.client.get(self.url, {'name': 'foo'})

        mock_get_appraisal_job_preview_files.assert_called_once()


class AppraisalJobViewSetRunTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.apprisal_job = AppraisalJob.objects.create()
        self.url = reverse('appraisaljob-run', args=(self.apprisal_job.pk,))

    def test_unauthenticated(self):
        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch('ESSArch_Core.maintenance.models.AppraisalJob.run')
    def test_authenticated_with_add_and_run_permissions(self, mock_appraisal_job_run):
        mock_appraisal_job_run.return_value = mock.ANY
        perm_list = [
            'add_appraisaljob',
            'run_appraisaljob',
        ]

        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_appraisal_job_run.assert_called_once()

    def test_authenticated_with_only_add_permission(self):
        perm_list = [
            'add_appraisaljob',
        ]

        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_with_only_run_permission(self):
        perm_list = [
            'run_appraisaljob',
        ]

        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AppraisalJobViewSetReportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.apprisal_job = AppraisalJob.objects.create()
        self.url = reverse('appraisaljob-report', args=(self.apprisal_job.pk,))

    def test_unauthenticated(self):
        response = self.client.get(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch('ESSArch_Core.maintenance.views.open')
    @mock.patch('ESSArch_Core.maintenance.views.MaintenanceJobViewSet.get_report_pdf_path')
    @mock.patch('ESSArch_Core.maintenance.views.generate_file_response')
    def test_authenticated(self, mock_generate_file_response, mock_get_report_pdf_path, mock_open):
        mock_generate_file_response.return_value = Response(status=status.HTTP_200_OK)
        mock_get_report_pdf_path.return_value = "report_path.pdf"
        mock_open.return_value = "dummy_stream"
        self.client.force_authenticate(user=self.user)

        self.client.get(self.url, {'name': 'foo'})

        mock_get_report_pdf_path.assert_called_once_with(str(self.apprisal_job.pk))
        mock_open.assert_called_once_with("report_path.pdf", 'rb')
        mock_generate_file_response.assert_called_once_with("dummy_stream", 'application/pdf')


class FindAllFilesTests(TestCase):

    def setUp(self):
        self.tmpdir = normalize_path(tempfile.mkdtemp())
        self.datadir = os.path.join(self.tmpdir, "datadir")
        self.addCleanup(shutil.rmtree, self.datadir)
        self.dir_names = [
            'a_dir', 'b_dir', 'c_dir',
            'aa_dir', 'bb_dir', 'cc_dir',
            'ab_dir', 'ac_dir',
            'ba_dir', 'bc_dir',
            'ca_dir', 'cb_dir',
            'a_dir/ca_dir', 'b_dir/cb_dir',
        ]
        self.ip = InformationPackage.objects.create(
            object_path=self.datadir,
            object_identifier_value="ip_obj_id_value"
        )

    def create_dirs_and_files(self):
        for d in self.dir_names:
            try:
                os.makedirs(os.path.join(self.datadir, d))
            except OSError as e:
                if e.errno != 17:
                    raise

        files = []
        for d in self.dir_names:
            for i in range(3):
                fname = os.path.join(self.datadir, os.path.join(d, f"{i}.txt"))
                with open(fname, 'w') as f:
                    f.write(f"{i}")
                files.append(fname)

        return files

    def normalize_paths(self, expected_file_names):
        return [win_to_posix(f) for f in expected_file_names]

    def test_find_all_files_when_pattern_is_star(self):
        files = self.create_dirs_and_files()
        expected_file_names = self.normalize_paths([fi.replace(os.path.join(self.datadir, ""), "") for fi in files])

        found_files = find_all_files(self.datadir, self.ip, "*")
        docs = self.normalize_paths([e['document'] for e in found_files])

        for e in found_files:
            self.assertEqual(e['ip'], 'ip_obj_id_value')

        self.assertCountEqual(expected_file_names, docs)

    def test_find_all_files_when_pattern_is_matching_pattern_which_ends_with_star(self):
        self.create_dirs_and_files()
        expected_file_names = self.normalize_paths([
            'a_dir/0.txt', 'a_dir/1.txt', 'a_dir/2.txt',
            'aa_dir/0.txt', 'aa_dir/1.txt', 'aa_dir/2.txt',
            'ab_dir/0.txt', 'ab_dir/1.txt', 'ab_dir/2.txt',
            'ac_dir/0.txt', 'ac_dir/1.txt', 'ac_dir/2.txt',
            'a_dir/ca_dir/0.txt', 'a_dir/ca_dir/1.txt', 'a_dir/ca_dir/2.txt',
        ])
        found_files = find_all_files(self.datadir, self.ip, "a*")
        docs = self.normalize_paths([e['document'] for e in found_files])

        for e in found_files:
            self.assertEqual(e['ip'], 'ip_obj_id_value')
        self.assertCountEqual(expected_file_names, docs)

    def test_find_all_files_when_pattern_is_matching_pattern_which_start_with_star(self):
        self.create_dirs_and_files()
        expected_file_names = self.normalize_paths([
            'a_dir/2.txt', 'aa_dir/2.txt', 'ab_dir/2.txt', 'ac_dir/2.txt', 'a_dir/ca_dir/2.txt',
            'b_dir/2.txt', 'ba_dir/2.txt', 'bb_dir/2.txt', 'bc_dir/2.txt', 'b_dir/cb_dir/2.txt',
            'c_dir/2.txt', 'ca_dir/2.txt', 'cb_dir/2.txt', 'cc_dir/2.txt',
        ])
        found_files = find_all_files(self.datadir, self.ip, "**/2.txt")
        docs = self.normalize_paths([e['document'] for e in found_files])

        for e in found_files:
            self.assertEqual(e['ip'], 'ip_obj_id_value')
        self.assertCountEqual(expected_file_names, docs)

    def test_find_all_files_when_pattern_is_matching_pattern_which_starts_and_ends_with_star(self):
        self.create_dirs_and_files()
        expected_file_names = self.normalize_paths([
            'a_dir/2.txt', 'aa_dir/2.txt', 'ab_dir/2.txt', 'ac_dir/2.txt', 'a_dir/ca_dir/2.txt',
            'b_dir/2.txt', 'ba_dir/2.txt', 'bb_dir/2.txt', 'bc_dir/2.txt', 'b_dir/cb_dir/2.txt',
            'c_dir/2.txt', 'ca_dir/2.txt', 'cb_dir/2.txt', 'cc_dir/2.txt',
        ])
        found_files = find_all_files(self.datadir, self.ip, "**/2*")
        docs = self.normalize_paths([e['document'] for e in found_files])

        for e in found_files:
            self.assertEqual(e['ip'], 'ip_obj_id_value')
        self.assertCountEqual(expected_file_names, docs)
