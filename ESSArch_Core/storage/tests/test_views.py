from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from ESSArch_Core.configuration.models import Path, StoragePolicy
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.storage.models import (
    DISK,
    STORAGE_TARGET_STATUS_ENABLED,
    STORAGE_TARGET_STATUS_MIGRATE,
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
