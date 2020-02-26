import os
import shutil
import tempfile
from unittest import mock

from celery import states as celery_states
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient, APITestCase

from ESSArch_Core.auth.models import Group, GroupType
from ESSArch_Core.configuration.models import Parameter, Path, StoragePolicy
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.maintenance.models import (
    AppraisalJob,
    AppraisalJobEntry,
    AppraisalTemplate,
    ConversionJob,
)
from ESSArch_Core.profiles.models import SubmissionAgreement
from ESSArch_Core.storage.models import (
    DISK,
    STORAGE_TARGET_STATUS_ENABLED,
    StorageMedium,
    StorageMethod,
    StorageMethodTargetRelation,
    StorageObject,
    StorageTarget,
)
from ESSArch_Core.storage.tests.helpers import (
    add_storage_medium,
    add_storage_obj,
)
from ESSArch_Core.tags.models import (
    Structure,
    StructureType,
    Tag,
    TagStructure,
    TagVersion,
    TagVersionType,
)
from ESSArch_Core.tags.tests.test_search import ESSArchSearchBaseTestCase
from ESSArch_Core.testing.runner import TaskRunner
from ESSArch_Core.util import normalize_path

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

        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)
        Path.objects.create(entity='appraisal_reports', value=tempfile.mkdtemp(dir=self.datadir))

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

        res = self.client.post(reverse('appraisaljob-list'), data={'package_file_pattern': ['logs/*']})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        res = self.client.post(reverse('appraisaljob-list'), data={'package_file_pattern': []})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        res = self.client.post(reverse('appraisaljob-list'), data={'package_file_pattern': None})
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

    def test_set(self):
        """
        When using POST we want to set the list of IPs added to the job
        to be exactly what we get as input
        """

        ip1 = InformationPackage.objects.create(archived=True)
        ip2 = InformationPackage.objects.create(archived=False)

        response = self.client.post(self.url, data={'information_packages': [ip1.pk, ip2.pk]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(self.url, data={'information_packages': [ip1.pk]})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertCountEqual(self.appraisal_job.information_packages.all(), [ip1])

        response = self.client.post(self.url, data={'information_packages': [ip1.pk, ip2.pk]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertCountEqual(self.appraisal_job.information_packages.all(), [ip1])

        ip2.archived = True
        ip2.save()
        response = self.client.post(self.url, data={'information_packages': [ip1.pk, ip2.pk]})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertCountEqual(self.appraisal_job.information_packages.all(), [ip1, ip2])

        response = self.client.post(self.url, data={'information_packages': [ip2.pk]})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertCountEqual(self.appraisal_job.information_packages.all(), [ip2])

    def test_add(self):
        """
        When using PATCH we want to update list of IPs added to the job
        by adding what we get as input to the existing list
        """

        ip1 = InformationPackage.objects.create(archived=True)
        ip2 = InformationPackage.objects.create(archived=False)

        response = self.client.patch(self.url, data={'information_packages': [ip1.pk, ip2.pk]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.patch(self.url, data={'information_packages': [ip1.pk]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(self.appraisal_job.information_packages.all(), [ip1])

        response = self.client.patch(self.url, data={'information_packages': [ip1.pk, ip2.pk]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertCountEqual(self.appraisal_job.information_packages.all(), [ip1])

        ip2.archived = True
        ip2.save()
        response = self.client.patch(self.url, data={'information_packages': [ip2.pk]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(self.appraisal_job.information_packages.all(), [ip1, ip2])

        response = self.client.patch(self.url, data={'information_packages': [ip2.pk]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
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

    def test_preview(self):
        datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, datadir)

        ip = InformationPackage.objects.create()
        self.appraisal_job.information_packages.add(ip)
        url = reverse('appraisal-job-information-packages-preview', args=(self.appraisal_job.pk, ip.pk))

        storage_target = StorageTarget.objects.create(target=tempfile.mkdtemp(dir=datadir))
        storage_medium = StorageMedium.objects.create(
            storage_target=storage_target,
            status=20, location_status=50, block_size=1024, format=103,
        )

        obj = StorageObject.objects.create(
            ip=ip, storage_medium=storage_medium,
            content_location_value=os.path.basename(tempfile.mkdtemp(dir=storage_target.target)),
            content_location_type=DISK,
        )

        test_dir = tempfile.mkdtemp(dir=obj.get_full_path())
        foo = os.path.join(test_dir, 'foo.txt')
        bar = os.path.join(test_dir, 'bar.txt')
        baz = os.path.join(test_dir, 'baz.pdf')
        open(foo, 'a').close()
        open(bar, 'a').close()
        open(baz, 'a').close()

        foo = normalize_path(os.path.relpath(foo, obj.get_full_path()))
        bar = normalize_path(os.path.relpath(bar, obj.get_full_path()))
        baz = normalize_path(os.path.relpath(baz, obj.get_full_path()))

        with self.subTest('no pattern'):
            res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertCountEqual(res.data, [foo, bar, baz])

        pattern = '*'
        with self.subTest(pattern):
            self.appraisal_job.package_file_pattern = [pattern]
            self.appraisal_job.save()

            res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertCountEqual(res.data, [foo, bar, baz])

        pattern = '**/*.txt'
        with self.subTest(pattern):
            self.appraisal_job.package_file_pattern = [pattern]
            self.appraisal_job.save()

            res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertCountEqual(res.data, [foo, bar])

        pattern = '**/baz.*'
        with self.subTest(pattern):
            self.appraisal_job.package_file_pattern = [pattern]
            self.appraisal_job.save()

            res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertCountEqual(res.data, [baz])


class AppraisalJobViewSetTagListViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username='user')
        self.client.force_authenticate(user=self.user)
        self.appraisal_job = AppraisalJob.objects.create()
        self.url = reverse('appraisal-job-tags-list', args=(self.appraisal_job.pk,))

    @mock.patch('ESSArch_Core.tags.serializers.Component.save')
    @mock.patch('ESSArch_Core.tags.serializers.Archive.save')
    def test_list(self, ma, mc):
        structure = Structure.objects.create(
            is_template=False,
            type=StructureType.objects.create()
        )

        archive_tag = Tag.objects.create()
        TagVersion.objects.create(
            tag=archive_tag, elastic_index='archive',
            type=TagVersionType.objects.create(archive_type=True, name='archive'),
            reference_code='a', name='foo_archive',
        )
        archive_tag_structure = TagStructure.objects.create(tag=archive_tag, structure=structure)
        self.appraisal_job.tags.add(archive_tag)

        tag_version_type = TagVersionType.objects.create(archive_type=False, name='component')
        for _ in range(100):
            tag = Tag.objects.create()
            TagVersion.objects.create(
                tag=tag, elastic_index='component',
                type=tag_version_type, reference_code='b',
                name='test_tag',
            )
            TagStructure.objects.create(tag=tag, parent=archive_tag_structure, structure=structure)
            self.appraisal_job.tags.add(tag)

        with self.assertNumQueries(2):
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            self.assertEqual(response.data[0]['id'], str(archive_tag.pk))
            self.assertEqual(response.data[0]['name'], 'foo_archive')
            self.assertEqual(response.data[0]['archive'], 'foo_archive')

            self.assertEqual(response.data[1]['name'], 'test_tag')
            self.assertEqual(response.data[1]['archive'], 'foo_archive')

        # test tags without versions or structures
        tag = Tag.objects.create()
        self.appraisal_job.tags.set([tag])

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_set(self):
        """
        When using POST we want to set the list of tags added to the job
        to be exactly what we get as input
        """

        tag1 = Tag.objects.create()
        tag2 = Tag.objects.create()

        response = self.client.post(self.url, data={'tags': [tag1.pk]})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertCountEqual(self.appraisal_job.tags.all(), [tag1])

        response = self.client.post(self.url, data={'tags': [tag2.pk]})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertCountEqual(self.appraisal_job.tags.all(), [tag2])

        response = self.client.post(self.url, data={'tags': [tag1.pk, tag2.pk]})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertCountEqual(self.appraisal_job.tags.all(), [tag1, tag2])

        response = self.client.post(self.url, data={'tags': [tag2.pk]})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertCountEqual(self.appraisal_job.tags.all(), [tag2])

    def test_add(self):
        """
        When using PATCH we want to update list of tags added to the job
        by adding what we get as input to the existing list
        """

        tag1 = Tag.objects.create()
        tag2 = Tag.objects.create()

        response = self.client.patch(self.url, data={'tags': [tag1.pk]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(self.appraisal_job.tags.all(), [tag1])

        response = self.client.patch(self.url, data={'tags': [tag2.pk]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(self.appraisal_job.tags.all(), [tag1, tag2])

    def test_delete(self):
        tag1 = Tag.objects.create()
        tag2 = Tag.objects.create()
        self.appraisal_job.tags.add(tag1, tag2)

        response = self.client.delete(self.url, data={'tags': [tag1.pk]})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertCountEqual(self.appraisal_job.tags.all(), [tag2])

        # verify that both tags still exists
        tag1.refresh_from_db()
        tag2.refresh_from_db()


class AppraisalJobViewSetRunTests(ESSArchSearchBaseTestCase):
    def setUp(self):
        self.user = User.objects.create(username='user')
        self.appraisal_job = AppraisalJob.objects.create(user=self.user)
        self.url = reverse('appraisaljob-run', args=(self.appraisal_job.pk,))

        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)
        Path.objects.create(entity='appraisal_reports', value=tempfile.mkdtemp(dir=self.datadir))
        Path.objects.create(entity='temp', value=tempfile.mkdtemp(dir=self.datadir))

        Parameter.objects.create(entity='agent_identifier_value', value='ESS')
        Parameter.objects.create(entity='event_identifier_type', value='ESS')
        Parameter.objects.create(entity='linking_agent_identifier_type', value='ESS')
        Parameter.objects.create(entity='linking_object_identifier_type', value='ESS')
        Parameter.objects.create(entity='medium_location', value='Media')

        Path.objects.create(entity='disseminations', value=tempfile.mkdtemp(dir=self.datadir))
        Path.objects.create(entity='ingest_reception', value=tempfile.mkdtemp(dir=self.datadir))
        ingest = Path.objects.create(entity='ingest', value=tempfile.mkdtemp(dir=self.datadir))
        receipts = Path.objects.create(entity='receipts', value=tempfile.mkdtemp(dir=self.datadir))
        os.makedirs(os.path.join(receipts.value, 'xml'))

        cache_storage_method = StorageMethod.objects.create()
        StorageMethodTargetRelation.objects.create(
            storage_method=cache_storage_method,
            storage_target=StorageTarget.objects.create(
                name='cache', target=tempfile.mkdtemp(dir=self.datadir),
            ),
            status=STORAGE_TARGET_STATUS_ENABLED,
        )
        policy = StoragePolicy.objects.create(
            cache_storage=cache_storage_method,
            ingest_path=ingest,
        )
        sa = SubmissionAgreement.objects.create(policy=policy)

        self.storage_method = StorageMethod.objects.create()
        policy.storage_methods.add(self.storage_method)
        target = StorageTarget.objects.create(target=tempfile.mkdtemp(dir=self.datadir))
        StorageMethodTargetRelation.objects.create(
            storage_method=self.storage_method,
            storage_target=target,
            status=STORAGE_TARGET_STATUS_ENABLED,
        )
        medium = add_storage_medium(target, 20, '1')

        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        self.ip = InformationPackage.objects.create(
            package_type=InformationPackage.AIP,
            aic=aic, generation=1, archived=True,
            responsible=self.user,
            submission_agreement=sa, submission_agreement_locked=True,
        )
        storage_obj = add_storage_obj(self.ip, medium, DISK, self.ip.object_identifier_value, create_dir=True)
        self.storage_path = storage_obj.get_full_path()
        foo = os.path.join(storage_obj.get_full_path(), 'foo')
        os.makedirs(foo)
        logs = os.path.join(storage_obj.get_full_path(), 'logs')
        os.makedirs(logs)
        storage_obj.open('foo.pdf', 'a').close()
        storage_obj.open('foo/bar.pdf', 'a').close()
        storage_obj.open('logs/1.log', 'a').close()
        storage_obj.open('logs/2.log', 'a').close()

        # add non-package files
        open(os.path.join(self.datadir, 'test.pdf'), 'a').close()
        open(os.path.join(self.datadir, 'example.log'), 'a').close()

    def test_unauthenticated(self):
        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @TaskRunner()
    @mock.patch('ESSArch_Core.maintenance.models.AppraisalJob.run')
    def test_authenticated_with_only_add_permission(self, mock_appraisal_job_run):
        mock_appraisal_job_run.return_value = mock.ANY
        perm_list = ['add_appraisaljob']

        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_appraisal_job_run.assert_not_called()

    @TaskRunner()
    @mock.patch('ESSArch_Core.maintenance.models.AppraisalJob.run')
    def test_prevent_running_already_running_job(self, mock_appraisal_job_run):
        mock_appraisal_job_run.return_value = mock.ANY
        perm_list = ['run_appraisaljob']
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))
        self.client.force_authenticate(user=self.user)

        self.appraisal_job.status = celery_states.STARTED
        self.appraisal_job.save()

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_appraisal_job_run.assert_not_called()

    @TaskRunner()
    @mock.patch('ESSArch_Core.maintenance.models.AppraisalJob.run')
    def test_prevent_running_completed_job(self, mock_appraisal_job_run):
        mock_appraisal_job_run.return_value = mock.ANY
        perm_list = ['run_appraisaljob']
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))
        self.client.force_authenticate(user=self.user)

        self.appraisal_job.status = celery_states.SUCCESS
        self.appraisal_job.save()

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_appraisal_job_run.assert_not_called()

    @TaskRunner()
    def test_delete_tags(self):
        perm_list = ['run_appraisaljob']
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))
        self.client.force_authenticate(user=self.user)

        tag = Tag.objects.create()
        tag_version_type = TagVersionType.objects.create()
        TagVersion.objects.create(tag=tag, type=tag_version_type, elastic_index='component')
        self.appraisal_job.tags.add(tag)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertFalse(Tag.objects.exists())

    @TaskRunner()
    @override_settings(DELETE_PACKAGES_ON_APPRAISAL=True)
    def test_delete_packages_no_file_pattern(self):
        perm_list = ['run_appraisaljob']
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))
        self.client.force_authenticate(user=self.user)

        self.appraisal_job.information_packages.add(self.ip)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(
            AppraisalJobEntry.objects.filter(
                job=self.appraisal_job, ip=None, document='foo.pdf',
            ).exists()
        )
        self.assertTrue(
            AppraisalJobEntry.objects.filter(
                job=self.appraisal_job, ip=None, document='foo/bar.pdf',
            ).exists()
        )
        with self.assertRaises(InformationPackage.DoesNotExist):
            self.ip.refresh_from_db()

        self.assertFalse(os.path.exists(self.storage_path))

        self.assertFalse(
            InformationPackage.objects.filter(
                package_type=InformationPackage.AIP, aic=self.ip.aic, generation=2,
                active=True,
            ).exists()
        )
        self.appraisal_job.refresh_from_db()
        self.assertEqual(self.appraisal_job.status, celery_states.SUCCESS)

    @TaskRunner()
    @override_settings(DELETE_PACKAGES_ON_APPRAISAL=True)
    def test_delete_packages_with_invalid_file_pattern(self):
        perm_list = ['run_appraisaljob']
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))
        self.client.force_authenticate(user=self.user)

        self.appraisal_job.information_packages.add(self.ip)
        self.appraisal_job.package_file_pattern = ['../../*.pdf', 'logs']
        self.appraisal_job.save()

        with self.assertRaises(ValueError):
            self.client.post(self.url)

        self.assertFalse(AppraisalJobEntry.objects.exists())
        self.ip.refresh_from_db()

        self.assertTrue(os.path.exists(self.storage_path))
        self.assertFalse(
            InformationPackage.objects.filter(
                package_type=InformationPackage.AIP, aic=self.ip.aic, generation=2,
                active=True,
            ).exists()
        )

    @TaskRunner()
    @override_settings(DELETE_PACKAGES_ON_APPRAISAL=True)
    def test_delete_packages_with_file_pattern(self):
        perm_list = ['run_appraisaljob']
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))
        self.client.force_authenticate(user=self.user)

        self.appraisal_job.information_packages.add(self.ip)
        self.appraisal_job.package_file_pattern = ['**/bar.*', 'logs']
        self.appraisal_job.save()

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertFalse(
            AppraisalJobEntry.objects.filter(
                job=self.appraisal_job, ip=None, document='foo.pdf',
            ).exists()
        )
        self.assertTrue(
            AppraisalJobEntry.objects.filter(
                job=self.appraisal_job, ip=None, document='foo/bar.pdf',
            ).exists()
        )
        with self.assertRaises(InformationPackage.DoesNotExist):
            self.ip.refresh_from_db()

        self.assertFalse(os.path.exists(self.storage_path))

        new_ip = InformationPackage.objects.get(
            package_type=InformationPackage.AIP, aic=self.ip.aic, generation=2,
            active=True,
        )
        new_storage = new_ip.storage.filter(
            storage_medium__storage_target__methods=self.storage_method
        ).get()
        new_path = new_storage.get_full_path()
        self.assertTrue(os.path.isfile(os.path.join(new_path, 'foo.pdf')))
        self.assertTrue(os.path.isdir(os.path.join(new_path, 'foo')))
        self.assertEqual(os.listdir(os.path.join(new_path, 'foo')), [])
        self.assertFalse(os.path.isdir(os.path.join(new_path, 'logs')))

    @TaskRunner()
    @override_settings(DELETE_PACKAGES_ON_APPRAISAL=False)
    def test_inactivate_packages_no_file_pattern(self):
        perm_list = ['run_appraisaljob']
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))
        self.client.force_authenticate(user=self.user)

        self.appraisal_job.information_packages.add(self.ip)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(
            AppraisalJobEntry.objects.filter(
                job=self.appraisal_job, ip=self.ip, document='foo.pdf',
            ).exists()
        )
        self.assertTrue(
            AppraisalJobEntry.objects.filter(
                job=self.appraisal_job, ip=self.ip, document='foo/bar.pdf',
            ).exists()
        )

        self.ip.refresh_from_db()
        self.assertFalse(self.ip.active)
        self.assertTrue(os.path.exists(self.storage_path))

        self.assertFalse(
            InformationPackage.objects.filter(
                package_type=InformationPackage.AIP, aic=self.ip.aic, generation=2,
                active=True,
            ).exists()
        )

    @TaskRunner()
    @override_settings(DELETE_PACKAGES_ON_APPRAISAL=False)
    def test_inactivate_packages_with_file_pattern(self):
        perm_list = ['run_appraisaljob']
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))
        self.client.force_authenticate(user=self.user)

        self.appraisal_job.information_packages.add(self.ip)
        self.appraisal_job.package_file_pattern = ['**/bar.*', 'logs']
        self.appraisal_job.save()

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertFalse(
            AppraisalJobEntry.objects.filter(
                job=self.appraisal_job, ip=self.ip, document='foo.pdf',
            ).exists()
        )
        self.assertTrue(
            AppraisalJobEntry.objects.filter(
                job=self.appraisal_job, ip=self.ip, document='foo/bar.pdf',
            ).exists()
        )

        self.ip.refresh_from_db()
        self.assertFalse(self.ip.active)

        self.assertTrue(os.path.exists(self.storage_path))

        new_ip = InformationPackage.objects.get(
            package_type=InformationPackage.AIP, aic=self.ip.aic, generation=2,
            active=True,
        )
        new_storage = new_ip.storage.filter(
            storage_medium__storage_target__methods=self.storage_method
        ).get()
        new_path = new_storage.get_full_path()
        self.assertTrue(os.path.isfile(os.path.join(new_path, 'foo.pdf')))
        self.assertTrue(os.path.isdir(os.path.join(new_path, 'foo')))
        self.assertEqual(os.listdir(os.path.join(new_path, 'foo')), [])
        self.assertFalse(os.path.isdir(os.path.join(new_path, 'logs')))


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
    @mock.patch('ESSArch_Core.maintenance.models.MaintenanceJob.get_report_pdf_path')
    @mock.patch('ESSArch_Core.maintenance.views.generate_file_response')
    def test_authenticated(self, mock_generate_file_response, mock_get_report_pdf_path, mock_open):
        mock_generate_file_response.return_value = Response(status=status.HTTP_200_OK)
        mock_get_report_pdf_path.return_value = "report_path.pdf"
        mock_open.return_value = "dummy_stream"
        self.client.force_authenticate(user=self.user)

        self.client.get(self.url, {'name': 'foo'})

        mock_get_report_pdf_path.assert_called_once_with()
        mock_open.assert_called_once_with("report_path.pdf", 'rb')
        mock_generate_file_response.assert_called_once_with("dummy_stream", 'application/pdf')


class ConversionJobViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create(username='user')
        self.client.force_authenticate(user=self.user)

        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)
        Path.objects.create(entity='conversion_reports', value=tempfile.mkdtemp(dir=self.datadir))

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
