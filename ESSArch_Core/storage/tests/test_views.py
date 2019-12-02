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
    TAPE,
    StorageMedium,
    StorageMethod,
    StorageMethodTargetRelation,
    StorageObject,
    StorageTarget,
)
from ESSArch_Core.WorkflowEngine.models import ProcessTask

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

        cls.policy = StoragePolicy.objects.create(
            cache_storage=StorageMethod.objects.create(),
            ingest_path=Path.objects.create(entity='test', value='foo')
        )

        cls.ip = InformationPackage.objects.create(archived=True, policy=cls.policy)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def add_storage_method_rel(self, storage_type, target_name, status):
        storage_method = StorageMethod.objects.create(
            type=storage_type,
        )
        storage_target = StorageTarget.objects.create(
            name=target_name,
        )

        return StorageMethodTargetRelation.objects.create(
            storage_method=storage_method,
            storage_target=storage_target,
            status=status,
        )

    def add_storage_medium(self, target, status):
        return StorageMedium.objects.create(
            storage_target=target,
            status=status, location_status=50, block_size=1024, format=103,
        )

    def add_storage_obj(self, ip, medium, loc_type, loc_value):
        return StorageObject.objects.create(
            ip=ip, storage_medium=medium,
            content_location_type=loc_type,
            content_location_value=loc_value,
        )


class StorageMigrationTests(StorageMigrationTestsBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.url = reverse('storage-migrations-list')

    @mock.patch('ESSArch_Core.ip.views.ProcessTask.run')
    def test_migrate(self, mock_task):
        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_MIGRATE)
        old_medium = self.add_storage_medium(old.storage_target, 20)
        self.add_storage_obj(self.ip, old_medium, DISK, '')

        new = self.add_storage_method_rel(DISK, 'new', STORAGE_TARGET_STATUS_ENABLED)

        self.policy.storage_methods.add(old.storage_method, new.storage_method)

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
        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_ENABLED)
        old_medium = self.add_storage_medium(old.storage_target, 20)
        self.add_storage_obj(self.ip, old_medium, DISK, '')

        new = self.add_storage_method_rel(DISK, 'new', STORAGE_TARGET_STATUS_ENABLED)

        self.policy.storage_methods.add(old.storage_method, new.storage_method)

        data = {
            'information_packages': [str(self.ip.pk)],
            'policy': str(self.policy.pk),
            'temp_path': 'temp',
            'storage_methods': [str(new.storage_method.pk)]
        }

        with self.subTest('enabled status'):
            response = self.client.post(self.url, data=data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            mock_task.assert_called_once()

        expected_msg = f'Invalid pk "{new.storage_method.pk}" - object does not exist.'

        with self.subTest('disabled status'):
            mock_task.reset_mock()
            new.status = STORAGE_TARGET_STATUS_DISABLED
            new.save()
            response = self.client.post(self.url, data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            msg = response.data['storage_methods'][0]
            self.assertEqual(msg, expected_msg)

            mock_task.assert_not_called()

        with self.subTest('migrate status'):
            mock_task.reset_mock()
            new.status = STORAGE_TARGET_STATUS_MIGRATE
            new.save()
            response = self.client.post(self.url, data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            msg = response.data['storage_methods'][0]
            self.assertEqual(msg, expected_msg)

            mock_task.assert_not_called()

        with self.subTest('read-only status'):
            mock_task.reset_mock()
            new.status = STORAGE_TARGET_STATUS_READ_ONLY
            new.save()
            response = self.client.post(self.url, data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            msg = response.data['storage_methods'][0]
            self.assertEqual(msg, expected_msg)

            mock_task.assert_not_called()

    @mock.patch('ESSArch_Core.ip.views.ProcessTask.run')
    def test_ip_with_no_storage(self, mock_task):
        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_ENABLED)
        new = self.add_storage_method_rel(DISK, 'new', STORAGE_TARGET_STATUS_ENABLED)

        self.policy.storage_methods.add(old.storage_method, new.storage_method)

        ip = InformationPackage.objects.create(policy=self.policy)
        data = {
            'information_packages': [str(ip.pk)],
            'policy': str(self.policy.pk),
            'temp_path': 'temp',
        }
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_task.assert_not_called()

    @mock.patch('ESSArch_Core.storage.serializers.ProcessTask', side_effect=ProcessTask)
    @mock.patch('ESSArch_Core.storage.serializers.ProcessTask.run')
    def test_migration_task_order(self, mock_task_run, mock_task):
        old = self.add_storage_method_rel(TAPE, 'old', STORAGE_TARGET_STATUS_ENABLED)
        old_medium = self.add_storage_medium(old.storage_target, 20)

        tape_ips = [
            InformationPackage.objects.create(archived=True, policy=self.policy)
            for _ in range(6)
        ]

        tape_location_values = ['1', '4', '5', '3', '10', '2']
        for idx, ip in enumerate(tape_ips):
            self.add_storage_obj(ip, old_medium, TAPE, tape_location_values[idx])

        disk_ips = [
            InformationPackage.objects.create(archived=True, policy=self.policy)
            for _ in range(6)
        ]

        disk_location_values = ['foo/bar', '0', '/data/test', '/data/test/aic', '1', 'baz']
        for idx, ip in enumerate(disk_ips):
            self.add_storage_obj(ip, old_medium, DISK, disk_location_values[idx])

        ips = tape_ips + disk_ips

        new = self.add_storage_method_rel(DISK, 'new', STORAGE_TARGET_STATUS_ENABLED)
        self.policy.storage_methods.add(old.storage_method, new.storage_method)

        data = {
            'information_packages': [str(ip.pk) for ip in ips],
            'policy': str(self.policy.pk),
            'temp_path': 'temp',
            'storage_methods': [str(new.storage_method.pk)]
        }

        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        class MockValidator(object):
            def __init__(self, validator):
                # validator is a function that takes a single argument and returns a bool.
                self.validator = validator

            def __eq__(self, other):
                return bool(self.validator(other))

        mock_task.assert_has_calls([
            mock.call(
                name='ESSArch_Core.storage.tasks.StorageMigration',
                label=mock.ANY,
                args=mock.ANY,
                information_package=MockValidator(lambda x: ip in disk_ips),
                responsible=mock.ANY,
                eager=False,
            ) for _ in range(6)] + [
            mock.call(
                name='ESSArch_Core.storage.tasks.StorageMigration',
                label=mock.ANY,
                args=mock.ANY,
                information_package=ip,
                responsible=mock.ANY,
                eager=False,
            ) for ip in [
                tape_ips[0],
                tape_ips[5],
                tape_ips[3],
                tape_ips[1],
                tape_ips[2],
                tape_ips[4],
            ]],
        )


class StorageMigrationPreviewTests(StorageMigrationTestsBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.url = reverse('storage-migrations-preview')

    def test_preview_with_migratable_ip(self):
        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_MIGRATE)
        old_medium = self.add_storage_medium(old.storage_target, 20)
        self.add_storage_obj(self.ip, old_medium, DISK, '')

        new = self.add_storage_method_rel(DISK, 'new', STORAGE_TARGET_STATUS_ENABLED)

        self.policy.storage_methods.add(old.storage_method, new.storage_method)
        data = {
            'information_packages': [str(self.ip.pk)],
            'policy': str(self.policy.pk),
        }
        res = self.client.get(self.url, data=data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_pagination(self):
        ip = InformationPackage.objects.create(archived=True, policy=self.policy)

        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_MIGRATE)
        self.policy.storage_methods.add(old.storage_method)
        old_medium = self.add_storage_medium(old.storage_target, 20)
        self.add_storage_obj(self.ip, old_medium, DISK, '')
        self.add_storage_obj(ip, old_medium, DISK, '')

        target = StorageTarget.objects.create(name='new target, old method')
        StorageMethodTargetRelation.objects.create(
            storage_method=old.storage_method,
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
        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_ENABLED)
        old_medium = self.add_storage_medium(old.storage_target, 20)
        self.add_storage_obj(self.ip, old_medium, DISK, '')

        new = self.add_storage_method_rel(DISK, 'new', STORAGE_TARGET_STATUS_ENABLED)
        self.policy.storage_methods.add(old.storage_method, new.storage_method)

        with self.subTest('old storage method'):
            data = {
                'information_packages': [str(self.ip.pk)],
                'storage_methods': [str(old.storage_method.pk)],
                'policy': str(self.policy.pk),
            }
            res = self.client.get(self.url, data=data)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(len(res.data), 0)

        with self.subTest('old storage method with new target'):
            old.status = STORAGE_TARGET_STATUS_MIGRATE
            old.save()

            target = StorageTarget.objects.create(name='new target, old method')
            StorageMethodTargetRelation.objects.create(
                storage_method=old.storage_method,
                storage_target=target,
                status=STORAGE_TARGET_STATUS_ENABLED,
            )

            data = {
                'information_packages': [str(self.ip.pk)],
                'storage_methods': [str(old.storage_method.pk)],
                'policy': str(self.policy.pk),
            }
            res = self.client.get(self.url, data=data)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(len(res.data), 1)

        with self.subTest('new storage method'):
            data = {
                'information_packages': [str(self.ip.pk)],
                'storage_methods': [str(new.storage_method.pk)],
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
    def test_preview_with_migratable_ip(self):
        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_ENABLED)
        old_medium = self.add_storage_medium(old.storage_target, 20)
        self.add_storage_obj(self.ip, old_medium, DISK, '')

        new = self.add_storage_method_rel(DISK, 'new', STORAGE_TARGET_STATUS_ENABLED)
        self.policy.storage_methods.add(old.storage_method, new.storage_method)

        data = {
            'policy': str(self.policy.pk),
        }
        url = reverse('storage-migrations-preview-detail', args=(str(self.ip.pk),))
        res = self.client.get(url, data=data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(new.storage_target.pk))

        old.status = STORAGE_TARGET_STATUS_MIGRATE
        old.save()

        target = StorageTarget.objects.create(name='new target, old method')
        StorageMethodTargetRelation.objects.create(
            storage_method=old.storage_method,
            storage_target=target,
            status=STORAGE_TARGET_STATUS_ENABLED,
        )

        res = self.client.get(url, data=data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_preview_with_specified_storage_method(self):
        url = reverse('storage-migrations-preview-detail', args=(str(self.ip.pk),))

        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_MIGRATE)
        old_medium = self.add_storage_medium(old.storage_target, 20)
        self.add_storage_obj(self.ip, old_medium, DISK, '')

        new = self.add_storage_method_rel(DISK, 'new', STORAGE_TARGET_STATUS_ENABLED)
        self.policy.storage_methods.add(old.storage_method, new.storage_method)

        with self.subTest('old storage method with new target'):
            target = StorageTarget.objects.create(name='new target, old method')
            StorageMethodTargetRelation.objects.create(
                storage_method=old.storage_method,
                storage_target=target,
                status=STORAGE_TARGET_STATUS_ENABLED,
            )

            data = {
                'storage_methods': [str(old.storage_method.pk)],
                'policy': str(self.policy.pk),
            }
            res = self.client.get(url, data=data)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(len(res.data), 1)
            self.assertEqual(res.data[0]['id'], str(target.pk))

        with self.subTest('new storage method'):
            data = {
                'storage_methods': [str(new.storage_method.pk)],
                'policy': str(self.policy.pk),
            }
            res = self.client.get(url, data=data)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(len(res.data), 1)
            self.assertEqual(res.data[0]['id'], str(new.storage_target.pk))

    def test_preview_with_non_migratable_ip(self):
        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_ENABLED)
        old_medium = self.add_storage_medium(old.storage_target, 20)
        self.add_storage_obj(self.ip, old_medium, DISK, '')

        new = self.add_storage_method_rel(DISK, 'new', STORAGE_TARGET_STATUS_ENABLED)
        self.policy.storage_methods.add(old.storage_method, new.storage_method)

        ip = InformationPackage.objects.create()
        data = {
            'policy': str(self.policy.pk),
        }
        url = reverse('storage-migrations-preview-detail', args=(str(ip.pk),))
        res = self.client.get(url, data=data)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
