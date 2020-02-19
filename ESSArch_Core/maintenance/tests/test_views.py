import os
import shutil
import tempfile
from unittest import mock

from celery import states as celery_states
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient, APITestCase

from ESSArch_Core.auth.models import Group, GroupType
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.maintenance.models import (
    AppraisalJob,
    AppraisalTemplate,
    ConversionJob,
    ConversionTemplate,
)
from ESSArch_Core.storage.models import (
    DISK,
    StorageMedium,
    StorageObject,
    StorageTarget,
)
from ESSArch_Core.testing.runner import TaskRunner

User = get_user_model()


class CreateAppraisalTemplateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username='user')
        self.url = reverse('appraisaltemplate-list')

    def test_unauthenticated(self):
        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_with_permission(self):
        perm = Permission.objects.get(codename='add_appraisaltemplate')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(self.url, {'name': 'bar', 'public': False})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        org_group_type = GroupType.objects.create(codename='organization')
        group = Group.objects.create(name='organization', group_type=org_group_type)
        group.add_member(self.user.essauth_member)

        response = self.client.post(self.url, {'name': 'bar', 'public': False})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ChangeAppraisalTemplateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username='user')
        self.template = AppraisalTemplate.objects.create()
        self.url = reverse('appraisaltemplate-detail', args=(self.template.pk,))

    def test_unauthenticated(self):
        response = self.client.patch(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_with_permission(self):
        perm = Permission.objects.get(codename='change_appraisaltemplate')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.patch(self.url, {'public': False})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        org_group_type = GroupType.objects.create(codename='organization')
        group = Group.objects.create(name='organization', group_type=org_group_type)
        group.add_member(self.user.essauth_member)

        response = self.client.patch(self.url, {'public': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AppraisalJobViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username='user')
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        appraisal_job = AppraisalJob.objects.create()
        res = self.client.get(reverse('appraisaljob-list'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(appraisal_job.pk))

    def test_create_without_permission(self):
        res = self.client.post(reverse('appraisaljob-list'))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_with_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename='add_appraisaljob'))
        res = self.client.post(reverse('appraisaljob-list'))
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_change_without_permission(self):
        appraisal_job = AppraisalJob.objects.create()
        res = self.client.patch(reverse('appraisaljob-detail', args=(appraisal_job.pk,)))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_change_with_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename='change_appraisaljob'))

        with self.subTest('status: {}'.format(celery_states.STARTED)):
            appraisal_job = AppraisalJob.objects.create(status=celery_states.STARTED)
            res = self.client.patch(reverse('appraisaljob-detail', args=(appraisal_job.pk,)))
            self.assertEqual(res.status_code, status.HTTP_423_LOCKED)

        for state in celery_states.READY_STATES | {celery_states.PENDING}:
            with self.subTest('status: {}'.format(state)):
                appraisal_job = AppraisalJob.objects.create(status=state)
                res = self.client.patch(reverse('appraisaljob-detail', args=(appraisal_job.pk,)))
                self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_delete_without_permission(self):
        appraisal_job = AppraisalJob.objects.create()
        res = self.client.delete(reverse('appraisaljob-detail', args=(appraisal_job.pk,)))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_with_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename='delete_appraisaljob'))

        with self.subTest('status: {}'.format(celery_states.STARTED)):
            appraisal_job = AppraisalJob.objects.create(status=celery_states.STARTED)
            res = self.client.delete(reverse('appraisaljob-detail', args=(appraisal_job.pk,)))
            self.assertEqual(res.status_code, status.HTTP_423_LOCKED)

        for state in celery_states.READY_STATES | {celery_states.PENDING}:
            with self.subTest('status: {}'.format(state)):
                appraisal_job = AppraisalJob.objects.create(status=state)
                res = self.client.delete(reverse('appraisaljob-detail', args=(appraisal_job.pk,)))
                self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)


class AppraisalJobViewSetInformationPackageListViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username='user')
        self.client.force_authenticate(user=self.user)
        self.appraisal_job = AppraisalJob.objects.create()
        self.url = reverse('appraisal-job-information-packages-list', args=(self.appraisal_job.pk,))

    def test_list(self):
        ip = InformationPackage.objects.create()
        self.appraisal_job.information_packages.add(ip)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['id'], str(ip.pk))

    def test_add(self):
        ip1 = InformationPackage.objects.create(archived=True)
        ip2 = InformationPackage.objects.create(archived=False)

        response = self.client.post(self.url, data={'information_packages': [ip1.pk, ip2.pk]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        ip2.archived = True
        ip2.save()
        response = self.client.post(self.url, data={'information_packages': [ip1.pk, ip2.pk]})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertCountEqual(self.appraisal_job.information_packages.all(), [ip1, ip2])

    def test_delete(self):
        ip1 = InformationPackage.objects.create(archived=True)
        ip2 = InformationPackage.objects.create(archived=True)
        self.appraisal_job.information_packages.add(ip1, ip2)

        response = self.client.delete(self.url, data={'information_packages': [ip1.pk]})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertCountEqual(self.appraisal_job.information_packages.all(), [ip2])

        # verify that both IP still exists
        ip1.refresh_from_db()
        ip2.refresh_from_db()


class AppraisalJobViewSetPreviewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username='user')
        self.appraisal_job = AppraisalJob.objects.create()
        self.url = reverse('appraisaljob-preview', args=(self.appraisal_job.pk,))

        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

    def test_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        self.client.force_authenticate(user=self.user)

        ip = InformationPackage.objects.create()
        self.appraisal_job.information_packages.add(ip)
        storage_target = StorageTarget.objects.create()
        storage_medium = StorageMedium.objects.create(
            storage_target=storage_target,
            status=20, location_status=50, block_size=1024, format=103,
        )

        obj = StorageObject.objects.create(
            ip=ip, storage_medium=storage_medium,
            content_location_value=tempfile.mkdtemp(dir=self.datadir),
            content_location_type=DISK,
        )

        test_dir = tempfile.mkdtemp(dir=obj.content_location_value)
        foo = os.path.join(test_dir, 'foo.txt')
        bar = os.path.join(test_dir, 'bar.txt')
        baz = os.path.join(test_dir, 'baz.pdf')
        open(foo, 'a').close()
        open(bar, 'a').close()
        open(baz, 'a').close()

        foo = os.path.relpath(foo, obj.content_location_value)
        bar = os.path.relpath(bar, obj.content_location_value)
        baz = os.path.relpath(baz, obj.content_location_value)

        with self.subTest('no pattern'):
            res = self.client.get(self.url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertCountEqual(
                res.data,
                [
                    {'ip': ip.object_identifier_value, 'document': foo},
                    {'ip': ip.object_identifier_value, 'document': bar},
                    {'ip': ip.object_identifier_value, 'document': baz},
                ]
            )

        pattern = '*'
        with self.subTest(pattern):
            self.appraisal_job.package_file_pattern = [pattern]
            self.appraisal_job.save()

            res = self.client.get(self.url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertCountEqual(
                res.data,
                [
                    {'ip': ip.object_identifier_value, 'document': foo},
                    {'ip': ip.object_identifier_value, 'document': bar},
                    {'ip': ip.object_identifier_value, 'document': baz},
                ]
            )

        pattern = '**/*.txt'
        with self.subTest(pattern):
            self.appraisal_job.package_file_pattern = [pattern]
            self.appraisal_job.save()

            res = self.client.get(self.url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertCountEqual(
                res.data,
                [
                    {'ip': ip.object_identifier_value, 'document': foo},
                    {'ip': ip.object_identifier_value, 'document': bar},
                ]
            )

        pattern = '**/baz.*'
        with self.subTest(pattern):
            self.appraisal_job.package_file_pattern = [pattern]
            self.appraisal_job.save()

            res = self.client.get(self.url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertCountEqual(
                res.data,
                [
                    {'ip': ip.object_identifier_value, 'document': baz},
                ]
            )


class AppraisalJobViewSetRunTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.appraisal_job = AppraisalJob.objects.create()
        self.url = reverse('appraisaljob-run', args=(self.appraisal_job.pk,))

    def test_unauthenticated(self):
        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @TaskRunner()
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

    @TaskRunner()
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

    @TaskRunner()
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
        self.appraisal_job = AppraisalJob.objects.create()
        self.url = reverse('appraisaljob-report', args=(self.appraisal_job.pk,))

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

        mock_get_report_pdf_path.assert_called_once_with(str(self.appraisal_job.pk))
        mock_open.assert_called_once_with("report_path.pdf", 'rb')
        mock_generate_file_response.assert_called_once_with("dummy_stream", 'application/pdf')


class ConversionJobViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username='user')
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        conversion_job = ConversionJob.objects.create()
        res = self.client.get(reverse('conversionjob-list'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(conversion_job.pk))

    def test_create_without_permission(self):
        res = self.client.post(reverse('conversionjob-list'))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_with_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename='add_conversionjob'))
        res = self.client.post(reverse('conversionjob-list'))
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_change_without_permission(self):
        conversion_job = ConversionJob.objects.create()
        res = self.client.patch(reverse('conversionjob-detail', args=(conversion_job.pk,)))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_change_with_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename='change_conversionjob'))

        with self.subTest('status: {}'.format(celery_states.STARTED)):
            conversion_job = ConversionJob.objects.create(status=celery_states.STARTED)
            res = self.client.patch(reverse('conversionjob-detail', args=(conversion_job.pk,)))
            self.assertEqual(res.status_code, status.HTTP_423_LOCKED)

        for state in celery_states.READY_STATES | {celery_states.PENDING}:
            with self.subTest('status: {}'.format(state)):
                conversion_job = ConversionJob.objects.create(status=state)
                res = self.client.patch(reverse('conversionjob-detail', args=(conversion_job.pk,)))
                self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_delete_without_permission(self):
        conversion_job = ConversionJob.objects.create()
        res = self.client.delete(reverse('conversionjob-detail', args=(conversion_job.pk,)))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_with_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename='delete_conversionjob'))

        with self.subTest('status: {}'.format(celery_states.STARTED)):
            conversion_job = ConversionJob.objects.create(status=celery_states.STARTED)
            res = self.client.delete(reverse('conversionjob-detail', args=(conversion_job.pk,)))
            self.assertEqual(res.status_code, status.HTTP_423_LOCKED)

        for state in celery_states.READY_STATES | {celery_states.PENDING}:
            with self.subTest('status: {}'.format(state)):
                conversion_job = ConversionJob.objects.create(status=state)
                res = self.client.delete(reverse('conversionjob-detail', args=(conversion_job.pk,)))
                self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)


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
    @mock.patch('ESSArch_Core.maintenance.models.ConversionJob.preview')
    def test_authenticated(self, mock_preview, mock_get_object):
        mock_get_object.return_value = ConversionJob()
        mock_get_object.return_value.template = ConversionTemplate()
        mock_preview.return_value = ["file1", "file2"]
        self.client.force_authenticate(user=self.user)

        self.client.get(self.url, {'name': 'foo'})

        mock_preview.assert_called_once()
