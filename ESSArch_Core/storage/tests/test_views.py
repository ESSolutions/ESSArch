from unittest import mock

from celery import states as celery_states
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from ESSArch_Core.configuration.models import Path, StoragePolicy
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.profiles.models import SubmissionAgreement
from ESSArch_Core.storage.models import (
    DISK,
    STORAGE_TARGET_STATUS_DISABLED,
    STORAGE_TARGET_STATUS_ENABLED,
    STORAGE_TARGET_STATUS_MIGRATE,
    STORAGE_TARGET_STATUS_READ_ONLY,
    TAPE,
    Robot,
    StorageMedium,
    StorageMethod,
    StorageMethodTargetRelation,
    StorageObject,
    StorageTarget,
    TapeDrive,
    TapeSlot,
)
from ESSArch_Core.testing.runner import TaskRunner
from ESSArch_Core.WorkflowEngine.models import ProcessTask

User = get_user_model()


class StorageMediumListTests(APITestCase):
    def setUp(self):
        user = User.objects.create(username='user')
        self.client = APIClient()
        self.client.force_authenticate(user=user)
        self.url = reverse('storagemedium-list')

    def test_sort_medium_id(self):
        storage_target = StorageTarget.objects.create()

        medium_ids = [
            'BA 100',
            'ABC',
            'X 1',
            'BA 1001',
            'XY 1',
            'XYZ 1',
            'BA 1',
            'BA 10',
            'BA 2',
            'BA 1002',
            'BA 1000',
            'BA 003',
            'QWE1',
            'QWE10',
            'QWE2',
            'A B 2',
            'A B 10',
            'DEF',
            'A B 1',
        ]

        for mid in medium_ids:
            StorageMedium.objects.create(
                medium_id=mid, storage_target=storage_target,
                status=20, location_status=50, block_size=1024, format=103,
            )

        res = self.client.get(self.url, {'ordering': 'medium_id', 'pager': 'none'})

        expected = [
            'ABC',
            'DEF',
            'QWE1',
            'QWE2',
            'QWE10',
            'A B 1',
            'A B 2',
            'A B 10',
            'BA 1',
            'BA 2',
            'BA 003',
            'BA 10',
            'BA 100',
            'BA 1000',
            'BA 1001',
            'BA 1002',
            'X 1',
            'XY 1',
            'XYZ 1',
        ]
        actual = [sm['medium_id'] for sm in res.data]

        self.assertEqual(expected, actual)


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

        cls.sa = SubmissionAgreement.objects.create(policy=cls.policy)
        cls.ip = InformationPackage.objects.create(archived=True, submission_agreement=cls.sa)
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
        self.storage_method_target_rel.status = STORAGE_TARGET_STATUS_MIGRATE
        self.storage_method_target_rel.save()

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
            submission_agreement=self.sa,
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
            submission_agreement=self.sa, active=False
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
        cls.user = User.objects.create(is_superuser=True)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('storagemedium-list')

        self.policy = StoragePolicy.objects.create(
            cache_storage=StorageMethod.objects.create(),
            ingest_path=Path.objects.create(entity='test', value='foo')
        )
        self.sa = SubmissionAgreement.objects.create(policy=self.policy)

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

    def add_storage_medium(self, target, status, medium_id):
        return StorageMedium.objects.create(
            storage_target=target, medium_id=medium_id,
            status=status, location_status=50, block_size=1024, format=103,
        )

    def add_storage_obj(self, ip, medium, loc_type, loc_value):
        return StorageObject.objects.create(
            ip=ip, storage_medium=medium,
            content_location_type=loc_type,
            content_location_value=loc_value,
        )

    def test_no_change(self):
        ip = InformationPackage.objects.create(archived=True, submission_agreement=self.sa)

        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_ENABLED)
        old_medium = self.add_storage_medium(old.storage_target, 20, '1')
        self.add_storage_obj(ip, old_medium, DISK, '')
        self.policy.storage_methods.add(old.storage_method)

        response = self.client.get(self.url, data={'migratable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        response = self.client.get(self.url, data={'migratable': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(old_medium.pk))

    def test_single_storage_method(self):
        ip = InformationPackage.objects.create(archived=True, submission_agreement=self.sa)

        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_MIGRATE)
        old_medium = self.add_storage_medium(old.storage_target, 20, '1')
        self.add_storage_obj(ip, old_medium, DISK, '')
        self.policy.storage_methods.add(old.storage_method)

        new_storage_target = StorageTarget.objects.create(name='new')
        new_rel = StorageMethodTargetRelation.objects.create(
            storage_method=old.storage_method,
            storage_target=new_storage_target,
            status=STORAGE_TARGET_STATUS_DISABLED
        )
        new_storage_medium = self.add_storage_medium(new_storage_target, 20, '2')

        # New target exists but it is disabled
        response = self.client.get(self.url, data={'migratable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        response = self.client.get(self.url, data={'migratable': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Enable new target
        new_rel.status = STORAGE_TARGET_STATUS_ENABLED
        new_rel.save()

        # New enabled target exists but no objects are migrated yet
        response = self.client.get(self.url, data={'migratable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(old_medium.pk))

        # Add IP to new medium
        StorageObject.objects.create(
            ip=ip, storage_medium=new_storage_medium,
            content_location_type=DISK,
        )

        # All objects migrated and old medium is deactivatable
        response = self.client.get(self.url, data={'migratable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # Add new IP to old medium
        new_ip = InformationPackage.objects.create(
            archived=True,
            submission_agreement=self.sa,
        )
        StorageObject.objects.create(
            ip=new_ip, storage_medium=old_medium,
            content_location_type=DISK,
        )

        # All objects are not migrated
        response = self.client.get(self.url, data={'migratable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(old_medium.pk))

        # Add new IP to new medium
        StorageObject.objects.create(
            ip=new_ip, storage_medium=new_storage_medium,
            content_location_type=DISK,
        )

        # All objects migrated and old medium is deactivatable
        response = self.client.get(self.url, data={'migratable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_multiple_storage_methods(self):
        ip = InformationPackage.objects.create(archived=True, submission_agreement=self.sa)

        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_MIGRATE)
        old_medium = self.add_storage_medium(old.storage_target, 20, '1')
        self.add_storage_obj(ip, old_medium, DISK, '')

        new = self.add_storage_method_rel(DISK, 'new', STORAGE_TARGET_STATUS_ENABLED)
        self.policy.storage_methods.add(old.storage_method, new.storage_method)

        for rstatus in (STORAGE_TARGET_STATUS_MIGRATE, STORAGE_TARGET_STATUS_ENABLED, STORAGE_TARGET_STATUS_READ_ONLY):
            old.status = rstatus
            old.save()

            with self.subTest('old method-target rel status = %s' % old.get_status_display()):
                response = self.client.get(self.url, data={'migratable': True})
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 1)
                self.assertEqual(response.data[0]['id'], str(old_medium.pk))

        old.status = STORAGE_TARGET_STATUS_DISABLED
        old.save()
        with self.subTest('old method-target rel status = %s' % old.get_status_display()):
            response = self.client.get(self.url, data={'migratable': True})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 0)

        # add object to new method
        old.status = STORAGE_TARGET_STATUS_MIGRATE
        old.save()
        new_medium = self.add_storage_medium(new.storage_target, 20, '2')
        self.add_storage_obj(ip, new_medium, DISK, '')

        response = self.client.get(self.url, data={'migratable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_multiple_storage_policies(self):
        other_policy = StoragePolicy.objects.create(
            policy_id='other',
            cache_storage=self.policy.cache_storage,
            ingest_path=self.policy.ingest_path,
        )
        ip = InformationPackage.objects.create(archived=True, submission_agreement=self.sa)

        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_MIGRATE)
        old_medium = self.add_storage_medium(old.storage_target, 20, '1')
        self.add_storage_obj(ip, old_medium, DISK, '')
        self.policy.storage_methods.add(old.storage_method)

        new = self.add_storage_method_rel(DISK, 'new', STORAGE_TARGET_STATUS_ENABLED)
        other_policy.storage_methods.add(new.storage_method)

        for rstatus in (STORAGE_TARGET_STATUS_MIGRATE, STORAGE_TARGET_STATUS_ENABLED, STORAGE_TARGET_STATUS_READ_ONLY):
            old.status = rstatus
            old.save()

            with self.subTest('old method-target rel status = %s' % old.get_status_display()):
                response = self.client.get(self.url, data={'migratable': True})
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 0)

        old.status = STORAGE_TARGET_STATUS_DISABLED
        old.save()
        with self.subTest('old method-target rel status = %s' % old.get_status_display()):
            response = self.client.get(self.url, data={'migratable': True})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 0)

    def test_multiple_ips(self):
        ip1 = InformationPackage.objects.create(
            package_type=InformationPackage.AIP,
            archived=True,
            submission_agreement=self.sa,
        )
        ip2 = InformationPackage.objects.create(
            package_type=InformationPackage.AIP,
            archived=True,
            submission_agreement=self.sa,
        )

        # default
        default_rel = self.add_storage_method_rel(DISK, 'default', STORAGE_TARGET_STATUS_MIGRATE)
        default_medium = self.add_storage_medium(default_rel.storage_target, 20, 'default')

        new_target = StorageTarget.objects.create(name='new_target')
        new_rel = StorageMethodTargetRelation.objects.create(
            storage_method=default_rel.storage_method,
            storage_target=new_target,
            status=STORAGE_TARGET_STATUS_ENABLED
        )

        # long term
        long_term_rel = self.add_storage_method_rel(DISK, 'default_long_term', STORAGE_TARGET_STATUS_ENABLED)
        long_term_medium = self.add_storage_medium(long_term_rel.storage_target, 20, 'long_term')

        self.policy.storage_methods.add(
            default_rel.storage_method,
            new_rel.storage_method,
            long_term_rel.storage_method,
        )

        self.add_storage_obj(ip1, default_medium, DISK, '')
        self.add_storage_obj(ip1, long_term_medium, DISK, '')

        self.add_storage_obj(ip2, long_term_medium, DISK, '')

        response = self.client.get(self.url, data={'migratable': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertCountEqual(
            [response.data[0]['id'], response.data[1]['id']],
            [str(default_medium.pk), str(long_term_medium.pk)],
        )

        ip_list_url = reverse('informationpackage-list')
        response = self.client.get(ip_list_url, data={
            'medium': str(default_medium.pk),
            'migratable': True,
            'view_type': 'flat',
        })
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(ip1.pk))

        response = self.client.get(ip_list_url, data={
            'medium': str(long_term_medium.pk),
            'migratable': True,
            'view_type': 'flat',
        })
        self.assertEqual(len(response.data), 2)
        self.assertCountEqual(
            [response.data[0]['id'], response.data[1]['id']],
            [str(ip1.pk), str(ip2.pk)],
        )


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

        cls.sa = SubmissionAgreement.objects.create(policy=cls.policy)
        cls.ip = InformationPackage.objects.create(archived=True, submission_agreement=cls.sa)
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
        cls.sa = SubmissionAgreement.objects.create(policy=cls.policy)
        cls.ip = InformationPackage.objects.create(archived=True, submission_agreement=cls.sa)

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
        self.policy.storage_methods.add(old.storage_method)
        old_medium = self.add_storage_medium(old.storage_target, 20)
        self.add_storage_obj(self.ip, old_medium, DISK, '')

        StorageMethodTargetRelation.objects.create(
            storage_target=StorageTarget.objects.create(),
            storage_method=old.storage_method,
            status=STORAGE_TARGET_STATUS_ENABLED,
        )

        data = {
            'information_packages': [str(self.ip.pk)],
            'policy': str(self.policy.pk),
            'temp_path': 'temp',
        }
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_task.assert_called_once()

    @mock.patch('ESSArch_Core.ip.views.ProcessTask.run')
    def test_method_rel_states(self, mock_task):
        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_MIGRATE)
        old_medium = self.add_storage_medium(old.storage_target, 20)
        self.add_storage_obj(self.ip, old_medium, DISK, '')

        new = StorageMethodTargetRelation.objects.create(
            storage_target=StorageTarget.objects.create(),
            storage_method=old.storage_method,
            status=STORAGE_TARGET_STATUS_MIGRATE,
        )

        self.policy.storage_methods.add(old.storage_method, new.storage_method)

        data = {
            'information_packages': [str(self.ip.pk)],
            'policy': str(self.policy.pk),
            'temp_path': 'temp',
        }

        with self.subTest('old migrate, new migrate'):
            response = self.client.post(self.url, data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            mock_task.assert_not_called()

        with self.subTest('old migrate, new read-only'):
            new.status = STORAGE_TARGET_STATUS_READ_ONLY
            new.save()
            response = self.client.post(self.url, data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            mock_task.assert_not_called()

        with self.subTest('old migrate, new disabled'):
            new.status = STORAGE_TARGET_STATUS_DISABLED
            new.save()
            response = self.client.post(self.url, data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            mock_task.assert_not_called()

        with self.subTest('old migrate, new enabled'):
            new.status = STORAGE_TARGET_STATUS_ENABLED
            new.save()
            response = self.client.post(self.url, data=data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            mock_task.assert_called_once()

    @mock.patch('ESSArch_Core.ip.views.ProcessTask.run')
    def test_ip_with_no_storage(self, mock_task):
        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_ENABLED)
        new = self.add_storage_method_rel(DISK, 'new', STORAGE_TARGET_STATUS_ENABLED)

        self.policy.storage_methods.add(old.storage_method, new.storage_method)

        ip = InformationPackage.objects.create(submission_agreement=self.sa)
        data = {
            'information_packages': [str(ip.pk)],
            'policy': str(self.policy.pk),
            'temp_path': 'temp',
        }
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_task.assert_not_called()

    @mock.patch('ESSArch_Core.ip.views.ProcessTask.run')
    def test_bad_ip(self, mock_task):
        ip = InformationPackage.objects.create(submission_agreement=self.sa)

        data = {
            'information_packages': [str(ip.pk)],
            'policy': str(self.policy.pk),
            'temp_path': 'temp',
        }
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_task.assert_not_called()

    @mock.patch(
        'ESSArch_Core.storage.serializers.ProcessTask.objects.get_or_create',
        side_effect=ProcessTask.objects.get_or_create
    )
    @mock.patch('ESSArch_Core.storage.serializers.ProcessTask.run')
    def test_migration_task_order(self, mock_task_run, mock_task):
        old = self.add_storage_method_rel(TAPE, 'old', STORAGE_TARGET_STATUS_MIGRATE)
        old_medium = self.add_storage_medium(old.storage_target, 20)

        StorageMethodTargetRelation.objects.create(
            storage_target=StorageTarget.objects.create(),
            storage_method=old.storage_method,
            status=STORAGE_TARGET_STATUS_ENABLED,
        )
        self.policy.storage_methods.add(old.storage_method)

        ips = [
            InformationPackage.objects.create(archived=True, submission_agreement=self.sa)
            for _ in range(6)
        ]

        tape_location_values = ['1', '4', '5', '3', '10', '2']
        for idx, ip in enumerate(ips):
            self.add_storage_obj(ip, old_medium, TAPE, tape_location_values[idx])

        data = {
            'information_packages': [str(ip.pk) for ip in ips],
            'policy': str(self.policy.pk),
            'temp_path': 'temp',
        }

        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        mock_task.assert_has_calls([
            mock.call(
                name='ESSArch_Core.storage.tasks.StorageMigration',
                label=mock.ANY,
                status__in=mock.ANY,
                information_package=ip,
                defaults={
                    'args': mock.ANY,
                    'responsible': mock.ANY,
                    'eager': False,
                }
            ) for ip in [ips[0], ips[5], ips[3], ips[1], ips[2], ips[4]]
        ])

    @mock.patch('ESSArch_Core.ip.views.ProcessTask.run')
    def test_queue_duplicate_migrations(self, mock_task):
        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_MIGRATE)
        old_medium = self.add_storage_medium(old.storage_target, 20)
        self.add_storage_obj(self.ip, old_medium, DISK, '')

        StorageMethodTargetRelation.objects.create(
            storage_target=StorageTarget.objects.create(),
            storage_method=old.storage_method,
            status=STORAGE_TARGET_STATUS_ENABLED,
        )

        self.policy.storage_methods.add(old.storage_method)

        data = {
            'information_packages': [str(self.ip.pk)],
            'policy': str(self.policy.pk),
            'temp_path': 'temp',
        }

        for _ in range(5):
            response = self.client.post(self.url, data=data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data['temp_path'] = 'temp2'
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(ProcessTask.objects.count(), 1)
        mock_task.assert_called_once()

        with self.subTest('completed task'):
            ProcessTask.objects.update(status=celery_states.SUCCESS)
            mock_task.reset_mock()

            for _ in range(5):
                response = self.client.post(self.url, data=data)
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            self.assertEqual(ProcessTask.objects.count(), 2)
            mock_task.assert_called_once()


class StorageMigrationPreviewTests(StorageMigrationTestsBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.url = reverse('storage-migrations-preview')

    def test_preview_with_migratable_ip(self):
        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_MIGRATE)
        old_medium = self.add_storage_medium(old.storage_target, 20)
        self.add_storage_obj(self.ip, old_medium, DISK, '')

        StorageMethodTargetRelation.objects.create(
            storage_method=old.storage_method,
            storage_target=StorageTarget.objects.create(name='new_target'),
            status=STORAGE_TARGET_STATUS_ENABLED,
        )

        self.policy.storage_methods.add(old.storage_method)
        data = {
            'information_packages': [str(self.ip.pk)],
            'policy': str(self.policy.pk),
        }
        res = self.client.get(self.url, data=data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_pagination(self):
        ip = InformationPackage.objects.create(archived=True, submission_agreement=self.sa)

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
        old = self.add_storage_method_rel(DISK, 'old', STORAGE_TARGET_STATUS_MIGRATE)
        old_medium = self.add_storage_medium(old.storage_target, 20)
        self.add_storage_obj(self.ip, old_medium, DISK, '')

        new = StorageMethodTargetRelation.objects.create(
            storage_target=StorageTarget.objects.create(),
            storage_method=old.storage_method,
            status=STORAGE_TARGET_STATUS_ENABLED,
        )
        self.policy.storage_methods.add(old.storage_method)

        data = {
            'policy': str(self.policy.pk),
        }
        url = reverse('storage-migrations-preview-detail', args=(str(self.ip.pk),))
        res = self.client.get(url, data=data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(new.storage_target.pk))

        # new relation with new method and new target
        new_method_target = self.add_storage_method_rel(DISK, 'new', STORAGE_TARGET_STATUS_ENABLED)
        self.policy.storage_methods.add(new_method_target.storage_method)
        url = reverse('storage-migrations-preview-detail', args=(str(self.ip.pk),))
        res = self.client.get(url, data=data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
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


class RobotTests(APITestCase):
    def setUp(self):
        user = User.objects.create(is_superuser=True)
        self.client.force_authenticate(user=user)

    @TaskRunner()
    def test_inventory(self):
        robot = Robot.objects.create()

        for drive_id in range(4):
            TapeDrive.objects.create(drive_id=str(drive_id), device='/dev/st{}'.format(drive_id), robot=robot)

        for slot_id in range(2):
            TapeSlot.objects.create(slot_id=str(slot_id), medium_id='HPS00{}'.format(slot_id + 1), robot=robot)

        storage_target = StorageTarget.objects.create()

        StorageMedium.objects.create(
            medium_id='HPS001', storage_target=storage_target,
            status=20, location_status=50,
            block_size=1024, format=103,
            tape_slot=TapeSlot.objects.get(slot_id='0'),
        )
        StorageMedium.objects.create(
            medium_id='HPS002', storage_target=storage_target,
            status=20, location_status=50,
            block_size=1024, format=103,
        )

        output = '''
  Storage Changer /dev/sg8:4 Drives, 52 Slots ( 4 Import/Export )
Data Transfer Element 0:Full (Storage Element 0 Loaded):VolumeTag = HPS001L3
Data Transfer Element 1:Empty
Data Transfer Element 2:Empty
Data Transfer Element 3:Empty
      Storage Element 0:Empty
      Storage Element 1:Full :VolumeTag=HPS002L3'''

        with mock.patch('ESSArch_Core.storage.tape.Popen.communicate', return_value=(output, '')):
            url = reverse('robot-inventory', args=(robot.pk,))
            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

            t = ProcessTask.objects.get()
            self.assertEqual(t.status, celery_states.SUCCESS)

            self.assertEqual(StorageMedium.objects.get(medium_id='HPS001').tape_drive.drive_id, 0)
            self.assertEqual(StorageMedium.objects.get(medium_id='HPS001').tape_slot.slot_id, 0)

            self.assertIsNone(StorageMedium.objects.get(medium_id='HPS002').tape_drive)
            self.assertEqual(StorageMedium.objects.get(medium_id='HPS002').tape_slot.slot_id, 1)
