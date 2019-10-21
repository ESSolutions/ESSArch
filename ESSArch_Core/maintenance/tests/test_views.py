from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from ESSArch_Core.maintenance.models import (
    AppraisalJob,
    AppraisalRule,
    ConversionJob,
    ConversionRule,
)

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

    @mock.patch('ESSArch_Core.maintenance.views.ConversionJobViewSet.get_object')
    @mock.patch('ESSArch_Core.maintenance.models.ConversionRule.get_job_preview_files')
    def test_authenticated(self, mock_get_job_preview_files, mock_get_object):
        mock_get_object.return_value = ConversionJob()
        mock_get_object.return_value.rule = ConversionRule()
        mock_get_job_preview_files.return_value = ["file1", "file2"]
        self.client.force_authenticate(user=self.user)

        self.client.get(self.url, {'name': 'foo'})

        mock_get_job_preview_files.assert_called_once()


class AppraisalJobViewSetPreviewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.apprisal_job = AppraisalJob.objects.create()
        self.url = reverse('appraisaljob-preview', args=(self.apprisal_job.pk,))

    def test_unauthenticated(self):
        response = self.client.get(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch('ESSArch_Core.maintenance.views.AppraisalJobViewSet.get_object')
    @mock.patch('ESSArch_Core.maintenance.models.AppraisalRule.get_job_preview_files')
    def test_authenticated(self, mock_get_job_preview_files, mock_get_object):
        mock_get_object.return_value = AppraisalJob()
        mock_get_object.return_value.rule = AppraisalRule()
        mock_get_job_preview_files.return_value = ["file1", "file2"]
        self.client.force_authenticate(user=self.user)

        self.client.get(self.url, {'name': 'foo'})

        mock_get_job_preview_files.assert_called_once()


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

    @mock.patch('ESSArch_Core.maintenance.models.AppraisalJob.run')
    def test_authenticated_with_only_add_permission(self, mock_appraisal_job_run):
        mock_appraisal_job_run.return_value = mock.ANY
        perm_list = [
            'add_appraisaljob',
        ]

        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_appraisal_job_run.assert_not_called()

    @mock.patch('ESSArch_Core.maintenance.models.AppraisalJob.run')
    def test_authenticated_with_only_run_permission(self, mock_appraisal_job_run):
        mock_appraisal_job_run.return_value = mock.ANY
        perm_list = [
            'run_appraisaljob',
        ]

        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_appraisal_job_run.assert_called_once()


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
