from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ESSArch_Core.storage.models import (
    STORAGE_TARGET_STATUS_ENABLED,
    STORAGE_TARGET_STATUS_MIGRATE,
    StorageMethod,
    StorageMethodTargetRelation,
    StorageTarget,
)

User = get_user_model()


class StorageMethodAdminTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(is_staff=True, is_superuser=True)

    def setUp(self):
        self.client.force_login(self.user)

    def test_change_view(self):
        def create_data(old, new, old_state, new_state):
            return {
                'name': old.storage_method.name,
                'enabled': 'on',
                'type': 200,
                'storage_method_target_relations-TOTAL_FORMS': '2',
                'storage_method_target_relations-INITIAL_FORMS': '2',
                'storage_method_target_relations-MIN_NUM_FORMS': '0',
                'storage_method_target_relations-MAX_NUM_FORMS': '1000',
                'storage_method_target_relations-0-id': old.pk,
                'storage_method_target_relations-0-storage_method': old.storage_method.pk,
                'storage_method_target_relations-0-name': old.name,
                'storage_method_target_relations-0-status': old_state,
                'storage_method_target_relations-0-storage_target': old.storage_target.pk,
                'storage_method_target_relations-1-id': new.pk,
                'storage_method_target_relations-1-storage_method': new.storage_method.pk,
                'storage_method_target_relations-1-name': new.name,
                'storage_method_target_relations-1-status': new_state,
                'storage_method_target_relations-1-storage_target': new.storage_target.pk,
            }

        method = StorageMethod.objects.create()
        old = StorageMethodTargetRelation.objects.create(
            storage_method=method,
            storage_target=StorageTarget.objects.create(name='old'),
            status=STORAGE_TARGET_STATUS_MIGRATE,
        )
        new = StorageMethodTargetRelation.objects.create(
            storage_method=method,
            storage_target=StorageTarget.objects.create(name='new'),
            status=STORAGE_TARGET_STATUS_ENABLED,
        )
        url = reverse('admin:storage_storagemethod_change', args=(method.pk,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        with self.subTest('one migrate and one enabled target'):
            response = self.client.post(
                url, follow=True,
                data=create_data(old, new, STORAGE_TARGET_STATUS_MIGRATE, STORAGE_TARGET_STATUS_ENABLED),
            )
            self.assertNotIn('errors', response.context_data)

        with self.subTest('multiple enabled targets'):
            response = self.client.post(
                url, follow=True,
                data=create_data(old, new, STORAGE_TARGET_STATUS_ENABLED, STORAGE_TARGET_STATUS_ENABLED),
            )
            self.assertIn(
                'Only 1 target can be enabled for a storage method at a time',
                response.context_data['errors'],
            )
