from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from ESSArch_Core.configuration.models import Path, StoragePolicy
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.storage.models import (
    DISK,
    STORAGE_TARGET_STATUS_DISABLED,
    STORAGE_TARGET_STATUS_ENABLED,
    STORAGE_TARGET_STATUS_MIGRATE,
    STORAGE_TARGET_STATUS_READ_ONLY,
    StorageMedium,
    StorageMethod,
    StorageMethodTargetRelation,
    StorageObject,
    StorageTarget,
)

User = get_user_model()


class StorageMediumDeactivatableTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.storage_method = StorageMethod.objects.create()
        cls.storage_target = StorageTarget.objects.create()
        cls.storage_method_target_rel = StorageMethodTargetRelation.objects.create(
            storage_method=cls.storage_method,
            storage_target=cls.storage_target,
            status=STORAGE_TARGET_STATUS_ENABLED
        )
        cls.storage_medium = StorageMedium.objects.create(
            storage_target=cls.storage_target,
            status=20, location_status=50, block_size=1024, format=103,
        )

        cls.policy = StoragePolicy.objects.create(
            cache_storage=cls.storage_method,
            ingest_path=Path.objects.create(entity='test', value='foo')
        )
        cls.policy.storage_methods.add(cls.storage_method)

        cls.ip = InformationPackage.objects.create(archived=True, policy=cls.policy)
        cls.user = User.objects.create(username='user')

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('storagemedium-list')

    def test_no_change(self):
        response = self.client.get(self.url, data={'deactivatable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_migrated_ip(self):
        new_storage_target = StorageTarget.objects.create(name='new')
        StorageMethodTargetRelation.objects.create(
            storage_method=self.storage_method,
            storage_target=new_storage_target,
            status=STORAGE_TARGET_STATUS_ENABLED
        )
        new_storage_medium = StorageMedium.objects.create(
            medium_id="new_medium", storage_target=new_storage_target,
            status=20, location_status=50, block_size=1024, format=103,
        )
        self.storage_method_target_rel.status = STORAGE_TARGET_STATUS_MIGRATE
        self.storage_method_target_rel.save()

        # Add IP to old medium
        StorageObject.objects.create(
            ip=self.ip, storage_medium=self.storage_medium,
            content_location_type=DISK,
        )

        # New enabled medium exists but no objects are migrated yet
        response = self.client.get(self.url, data={'deactivatable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        # Add IP to new medium
        StorageObject.objects.create(
            ip=self.ip, storage_medium=new_storage_medium,
            content_location_type=DISK,
        )

        # All objects migrated and old medium is deactivatable
        response = self.client.get(self.url, data={'deactivatable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(self.storage_medium.pk))

        # Add new IP to old medium
        new_ip = InformationPackage.objects.create(
            archived=True,
            policy=self.policy
        )
        StorageObject.objects.create(
            ip=new_ip, storage_medium=self.storage_medium,
            content_location_type=DISK,
        )

        # All objects are not migrated
        response = self.client.get(self.url, data={'deactivatable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        # Add new IP to new medium
        StorageObject.objects.create(
            ip=new_ip, storage_medium=new_storage_medium,
            content_location_type=DISK,
        )

        # All objects migrated and old medium is deactivatable
        response = self.client.get(self.url, data={'deactivatable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(self.storage_medium.pk))

        # Add new inactive IP to old medium
        inactive_ip = InformationPackage.objects.create(
            archived=True,
            policy=self.policy, active=False
        )
        StorageObject.objects.create(
            ip=inactive_ip, storage_medium=self.storage_medium,
            content_location_type=DISK,
        )

        # Ignore inactive IPs, all objects are migrated,
        # and old medium is deactivatable
        response = self.client.get(self.url, data={'deactivatable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(self.storage_medium.pk))

        # Include inactive IPs, all objects are not migrated,
        # and old medium is not deactivatable
        response = self.client.get(self.url, data={'deactivatable': True, 'include_inactive_ips': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        # Add inactive IP to new medium
        StorageObject.objects.create(
            ip=inactive_ip, storage_medium=new_storage_medium,
            content_location_type=DISK,
        )

        # All objects migrated and old medium is deactivatable
        response = self.client.get(self.url, data={'deactivatable': True, 'include_inactive_ips': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(self.storage_medium.pk))

    def test_multiple_storage_methods(self):
        self.storage_method_target_rel.status = STORAGE_TARGET_STATUS_MIGRATE
        self.storage_method_target_rel.save()

        # Add IP to old medium
        StorageObject.objects.create(
            ip=self.ip, storage_medium=self.storage_medium,
            content_location_type=DISK,
        )

        # Add IP to new method
        new_storage_method = StorageMethod.objects.create(name="new_method")
        storage_target_in_new_method = StorageTarget.objects.create(name="target_in_new_method")
        StorageMethodTargetRelation.objects.create(
            storage_method=new_storage_method,
            storage_target=storage_target_in_new_method,
            status=STORAGE_TARGET_STATUS_ENABLED
        )
        storage_medium_in_new_method = StorageMedium.objects.create(
            medium_id="medium_in_new_method", storage_target=storage_target_in_new_method,
            status=20, location_status=50, block_size=1024, format=103,
        )
        StorageObject.objects.create(
            ip=self.ip, storage_medium=storage_medium_in_new_method,
            content_location_type=DISK,
        )

        response = self.client.get(self.url, data={'deactivatable': True, 'include_inactive_ips': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        # migrate IP from old medium to new medium on same method

        new_storage_target = StorageTarget.objects.create(name='new')
        StorageMethodTargetRelation.objects.create(
            storage_method=self.storage_method,
            storage_target=new_storage_target,
            status=STORAGE_TARGET_STATUS_ENABLED
        )
        new_storage_medium = StorageMedium.objects.create(
            medium_id="new_medium", storage_target=new_storage_target,
            status=20, location_status=50, block_size=1024, format=103,
        )

        StorageObject.objects.create(
            ip=self.ip, storage_medium=new_storage_medium,
            content_location_type=DISK,
        )

        # All objects migrated and old medium is deactivatable
        response = self.client.get(self.url, data={'deactivatable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(self.storage_medium.pk))


class StorageMediumMigratableTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.storage_method = StorageMethod.objects.create()
        cls.storage_target = StorageTarget.objects.create()
        cls.storage_method_target_rel = StorageMethodTargetRelation.objects.create(
            storage_method=cls.storage_method,
            storage_target=cls.storage_target,
            status=STORAGE_TARGET_STATUS_ENABLED
        )
        cls.storage_medium = StorageMedium.objects.create(
            storage_target=cls.storage_target,
            status=20, location_status=50, block_size=1024, format=103,
        )

        cls.policy = StoragePolicy.objects.create(
            cache_storage=cls.storage_method,
            ingest_path=Path.objects.create(entity='test', value='foo')
        )
        cls.policy.storage_methods.add(cls.storage_method)

        cls.ip = InformationPackage.objects.create(archived=True, policy=cls.policy)
        cls.user = User.objects.create(username='user')

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('storagemedium-list')

    def test_no_change(self):
        response = self.client.get(self.url, data={'migratable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        response = self.client.get(self.url, data={'migratable': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(self.storage_medium.pk))

    def test_migrated_ip(self):
        new_storage_target = StorageTarget.objects.create(name='new')
        new_rel = StorageMethodTargetRelation.objects.create(
            storage_method=self.storage_method,
            storage_target=new_storage_target,
            status=STORAGE_TARGET_STATUS_DISABLED
        )
        new_storage_medium = StorageMedium.objects.create(
            medium_id="new_medium", storage_target=new_storage_target,
            status=20, location_status=50, block_size=1024, format=103,
        )
        self.storage_method_target_rel.status = STORAGE_TARGET_STATUS_MIGRATE
        self.storage_method_target_rel.save()

        # Add IP to old medium
        StorageObject.objects.create(
            ip=self.ip, storage_medium=self.storage_medium,
            content_location_type=DISK,
        )

        # New medium exists but it is disabled
        response = self.client.get(self.url, data={'migratable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        response = self.client.get(self.url, data={'migratable': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Enable new medium
        new_rel.status = STORAGE_TARGET_STATUS_ENABLED
        new_rel.save()

        # New enabled medium exists but no objects are migrated yet
        response = self.client.get(self.url, data={'migratable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(self.storage_medium.pk))

        # Add IP to new medium
        StorageObject.objects.create(
            ip=self.ip, storage_medium=new_storage_medium,
            content_location_type=DISK,
        )

        # All objects migrated and old medium is deactivatable
        response = self.client.get(self.url, data={'migratable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        # Add new IP to old medium
        new_ip = InformationPackage.objects.create(
            archived=True,
            policy=self.policy
        )
        StorageObject.objects.create(
            ip=new_ip, storage_medium=self.storage_medium,
            content_location_type=DISK,
        )

        # All objects are not migrated
        response = self.client.get(self.url, data={'migratable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(self.storage_medium.pk))

        # Add new IP to new medium
        StorageObject.objects.create(
            ip=new_ip, storage_medium=new_storage_medium,
            content_location_type=DISK,
        )

        # All objects migrated and old medium is deactivatable
        response = self.client.get(self.url, data={'migratable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])


class StorageMediumDeactivateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.storage_method = StorageMethod.objects.create()
        cls.storage_target = StorageTarget.objects.create()
        cls.storage_method_target_rel = StorageMethodTargetRelation.objects.create(
            storage_method=cls.storage_method,
            storage_target=cls.storage_target,
            status=STORAGE_TARGET_STATUS_MIGRATE
        )

        new_storage_target = StorageTarget.objects.create(name='new')
        StorageMethodTargetRelation.objects.create(
            storage_method=cls.storage_method,
            storage_target=new_storage_target,
            status=STORAGE_TARGET_STATUS_ENABLED
        )
        cls.new_storage_medium = StorageMedium.objects.create(
            medium_id="new_medium", storage_target=new_storage_target,
            status=20, location_status=50, block_size=1024, format=103,
        )
        cls.policy = StoragePolicy.objects.create(
            cache_storage=cls.storage_method,
            ingest_path=Path.objects.create(entity='test', value='foo')
        )
        cls.policy.storage_methods.add(cls.storage_method)

        cls.ip = InformationPackage.objects.create(archived=True, policy=cls.policy)
        cls.user = User.objects.create(username='user')

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.storage_medium = StorageMedium.objects.create(
            storage_target=self.storage_target,
            status=20, location_status=50, block_size=1024, format=103,
        )
        self.url = reverse('storagemedium-deactivate', args=(self.storage_medium.pk,))

        StorageObject.objects.create(
            ip=self.ip, storage_medium=self.storage_medium,
            content_location_type=DISK,
        )

    def test_non_migrated_medium(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.storage_medium.refresh_from_db()
        self.assertEqual(self.storage_medium.status, 20)

    def test_migrated_ip(self):
        # Add IP to new medium
        StorageObject.objects.create(
            ip=self.ip, storage_medium=self.new_storage_medium,
            content_location_type=DISK,
        )

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.storage_medium.refresh_from_db()
        self.assertEqual(self.storage_medium.status, 0)

    def test_deactivated_migrated_medium(self):
        # Add IP to new medium
        StorageObject.objects.create(
            ip=self.ip, storage_medium=self.new_storage_medium,
            content_location_type=DISK,
        )
        self.storage_medium.status = 0
        self.storage_medium.save()

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.storage_medium.refresh_from_db()
        self.assertEqual(self.storage_medium.status, 0)


class StorageMethodListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='user')

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.url = reverse('storagemethod-list')

    def test_filter_has_migrate_target(self):
        storage_method1 = StorageMethod.objects.create()
        storage_target1 = StorageTarget.objects.create(name='1')

        storage_method2 = StorageMethod.objects.create()
        storage_target2 = StorageTarget.objects.create(name='2')

        response = self.client.get(self.url, data={'has_migrate_target': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        StorageMethodTargetRelation.objects.create(
            storage_method=storage_method1,
            storage_target=storage_target1,
            status=STORAGE_TARGET_STATUS_MIGRATE,
        )

        StorageMethodTargetRelation.objects.create(
            storage_method=storage_method2,
            storage_target=storage_target2,
            status=STORAGE_TARGET_STATUS_ENABLED,
        )

        response = self.client.get(self.url, data={'has_migrate_target': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(storage_method1.pk))

        response = self.client.get(self.url, data={'has_migrate_target': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(storage_method2.pk))

    def test_filter_has_enabled_target(self):
        storage_method1 = StorageMethod.objects.create()
        storage_target1 = StorageTarget.objects.create(name='1')

        storage_method2 = StorageMethod.objects.create()
        storage_target2 = StorageTarget.objects.create(name='2')

        response = self.client.get(self.url, data={'has_enabled_target': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        StorageMethodTargetRelation.objects.create(
            storage_method=storage_method1,
            storage_target=storage_target1,
            status=STORAGE_TARGET_STATUS_MIGRATE,
        )

        StorageMethodTargetRelation.objects.create(
            storage_method=storage_method2,
            storage_target=storage_target2,
            status=STORAGE_TARGET_STATUS_ENABLED,
        )

        response = self.client.get(self.url, data={'has_enabled_target': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(storage_method2.pk))

        response = self.client.get(self.url, data={'has_enabled_target': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(storage_method1.pk))


class StorageMigrationTestsBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='user', is_superuser=True)

        cls.storage_method = StorageMethod.objects.create()
        cls.storage_target = StorageTarget.objects.create()
        cls.storage_medium = StorageMedium.objects.create(
            storage_target=cls.storage_target,
            status=20, location_status=50, block_size=1024, format=103,
        )

        cls.policy = StoragePolicy.objects.create(
            cache_storage=cls.storage_method,
            ingest_path=Path.objects.create(entity='test', value='foo')
        )
        cls.policy.storage_methods.add(cls.storage_method)

        cls.ip = InformationPackage.objects.create(archived=True, policy=cls.policy)
        StorageObject.objects.create(
            ip=cls.ip, storage_medium=cls.storage_medium,
            content_location_type=DISK,
        )

        cls.new_storage_method = StorageMethod.objects.create()
        cls.policy.storage_methods.add(cls.new_storage_method)
        cls.new_storage_target = StorageTarget.objects.create(name='new')
        StorageMethodTargetRelation.objects.create(
            storage_method=cls.new_storage_method,
            storage_target=cls.new_storage_target,
            status=STORAGE_TARGET_STATUS_ENABLED
        )

    def setUp(self):
        self.storage_method_target_rel = StorageMethodTargetRelation.objects.create(
            storage_method=self.storage_method,
            storage_target=self.storage_target,
            status=STORAGE_TARGET_STATUS_ENABLED
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)


class StorageMigrationTests(StorageMigrationTestsBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.url = reverse('storage-migrations-list')

    @mock.patch('ESSArch_Core.ip.views.ProcessTask.run')
    def test_migrate(self, mock_task):
        data = {
            'information_packages': [str(self.ip.pk)],
            'policy': str(self.policy.pk),
            'temp_path': 'temp',
        }
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_task.assert_called_once()

    @mock.patch('ESSArch_Core.ip.views.ProcessTask.run')
    def test_storage_methods(self, mock_task):
        storage_method = StorageMethod.objects.create()
        self.policy.storage_methods.add(storage_method)

        storage_target = StorageTarget.objects.create(name='another target')

        data = {
            'information_packages': [str(self.ip.pk)],
            'policy': str(self.policy.pk),
            'temp_path': 'temp',
            'storage_methods': [str(storage_method.pk)]
        }

        storage_rel = StorageMethodTargetRelation.objects.create(
            storage_method=storage_method,
            storage_target=storage_target,
            status=STORAGE_TARGET_STATUS_ENABLED
        )

        with self.subTest('enabled status'):
            response = self.client.post(self.url, data=data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            mock_task.assert_called_once()

        expected_msg = f'Invalid pk "{storage_method.pk}" - object does not exist.'

        with self.subTest('disabled status'):
            mock_task.reset_mock()
            storage_rel.status = STORAGE_TARGET_STATUS_DISABLED
            storage_rel.save()
            response = self.client.post(self.url, data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            msg = response.data['storage_methods'][0]
            self.assertEqual(msg, expected_msg)

            mock_task.assert_not_called()

        with self.subTest('migrate status'):
            mock_task.reset_mock()
            storage_rel.status = STORAGE_TARGET_STATUS_MIGRATE
            storage_rel.save()
            response = self.client.post(self.url, data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            msg = response.data['storage_methods'][0]
            self.assertEqual(msg, expected_msg)

            mock_task.assert_not_called()

        with self.subTest('read-only status'):
            mock_task.reset_mock()
            storage_rel.status = STORAGE_TARGET_STATUS_READ_ONLY
            storage_rel.save()
            response = self.client.post(self.url, data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            msg = response.data['storage_methods'][0]
            self.assertEqual(msg, expected_msg)

            mock_task.assert_not_called()

    @mock.patch('ESSArch_Core.ip.views.ProcessTask.run')
    def test_bad_ip(self, mock_task):
        ip = InformationPackage.objects.create(policy=self.policy)
        data = {
            'information_packages': [str(ip.pk)],
            'policy': str(self.policy.pk),
            'temp_path': 'temp',
        }
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_task.assert_not_called()


class StorageMigrationPreviewTests(StorageMigrationTestsBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.url = reverse('storage-migrations-preview')

    def test_preview_with_migratable_ip(self):
        data = {
            'information_packages': [str(self.ip.pk)],
            'policy': str(self.policy.pk),
        }
        res = self.client.get(self.url, data=data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_pagination(self):
        ip = InformationPackage.objects.create(archived=True, policy=self.policy)
        StorageObject.objects.create(
            ip=ip, storage_medium=self.storage_medium,
            content_location_type=DISK,
        )

        self.storage_method_target_rel.status = STORAGE_TARGET_STATUS_MIGRATE
        self.storage_method_target_rel.save()

        target = StorageTarget.objects.create(name='new target, old method')
        StorageMethodTargetRelation.objects.create(
            storage_method=self.storage_method,
            storage_target=target,
            status=STORAGE_TARGET_STATUS_ENABLED,
        )

        data = {
            'information_packages': [str(self.ip.pk), str(ip.pk)],
            'policy': str(self.policy.pk),
        }
        res = self.client.get(self.url, data=data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

        data['page_size'] = 1
        res = self.client.get(self.url, data=data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        first_page_ip = res.data[0]

        data['page'] = 2
        res = self.client.get(self.url, data=data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        second_page_ip = res.data[0]

        self.assertNotEqual(first_page_ip, second_page_ip)

        data.pop('page')
        data.pop('page_size')
        data['pager'] = 'none'
        res = self.client.get(self.url, data=data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_preview_with_specified_storage_method(self):
        with self.subTest('old storage method'):
            data = {
                'information_packages': [str(self.ip.pk)],
                'storage_methods': [str(self.storage_method.pk)],
                'policy': str(self.policy.pk),
            }
            res = self.client.get(self.url, data=data)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(len(res.data), 0)

        with self.subTest('old storage method with new target'):
            self.storage_method_target_rel.status = STORAGE_TARGET_STATUS_MIGRATE
            self.storage_method_target_rel.save()

            target = StorageTarget.objects.create(name='new target, old method')
            StorageMethodTargetRelation.objects.create(
                storage_method=self.storage_method,
                storage_target=target,
                status=STORAGE_TARGET_STATUS_ENABLED,
            )

            data = {
                'information_packages': [str(self.ip.pk)],
                'storage_methods': [str(self.storage_method.pk)],
                'policy': str(self.policy.pk),
            }
            res = self.client.get(self.url, data=data)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(len(res.data), 1)

        with self.subTest('new storage method'):
            data = {
                'information_packages': [str(self.ip.pk)],
                'storage_methods': [str(self.new_storage_method.pk)],
                'policy': str(self.policy.pk),
            }
            res = self.client.get(self.url, data=data)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(len(res.data), 1)

    def test_preview_with_non_migratable_ip(self):
        ip = InformationPackage.objects.create()
        data = {
            'information_packages': [str(ip.pk)],
            'policy': str(self.policy.pk),
        }
        res = self.client.get(self.url, data=data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class StorageMigrationPreviewDetailTests(StorageMigrationTestsBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

    def test_preview_with_migratable_ip(self):
        data = {
            'policy': str(self.policy.pk),
        }
        url = reverse('storage-migrations-preview-detail', args=(str(self.ip.pk),))
        res = self.client.get(url, data=data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(self.new_storage_target.pk))

        self.storage_method_target_rel.status = STORAGE_TARGET_STATUS_MIGRATE
        self.storage_method_target_rel.save()

        target = StorageTarget.objects.create(name='new target, old method')
        StorageMethodTargetRelation.objects.create(
            storage_method=self.storage_method,
            storage_target=target,
            status=STORAGE_TARGET_STATUS_ENABLED,
        )

        res = self.client.get(url, data=data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_preview_with_specified_storage_method(self):
        url = reverse('storage-migrations-preview-detail', args=(str(self.ip.pk),))

        with self.subTest('old storage method with new target'):
            self.storage_method_target_rel.status = STORAGE_TARGET_STATUS_MIGRATE
            self.storage_method_target_rel.save()

            target = StorageTarget.objects.create(name='new target, old method')
            StorageMethodTargetRelation.objects.create(
                storage_method=self.storage_method,
                storage_target=target,
                status=STORAGE_TARGET_STATUS_ENABLED,
            )

            data = {
                'storage_methods': [str(self.storage_method.pk)],
                'policy': str(self.policy.pk),
            }
            res = self.client.get(url, data=data)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(len(res.data), 1)
            self.assertEqual(res.data[0]['id'], str(target.pk))

        with self.subTest('new storage method'):
            data = {
                'storage_methods': [str(self.new_storage_method.pk)],
                'policy': str(self.policy.pk),
            }
            res = self.client.get(url, data=data)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(len(res.data), 1)
            self.assertEqual(res.data[0]['id'], str(self.new_storage_target.pk))

    def test_preview_with_non_migratable_ip(self):
        ip = InformationPackage.objects.create()
        data = {
            'policy': str(self.policy.pk),
        }
        url = reverse('storage-migrations-preview-detail', args=(str(ip.pk),))
        res = self.client.get(url, data=data)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
