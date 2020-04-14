from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ESSArch_Core.configuration.models import Feature


class FeatureAdminTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(is_staff=True, is_superuser=True)

    def setUp(self):
        self.client.force_login(self.user)

    def test_add_view(self):
        response = self.client.get(reverse('admin:configuration_feature_add'))
        self.assertEqual(response.status_code, 200)

    def test_changelist_view(self):
        response = self.client.get(reverse('admin:configuration_feature_changelist'))
        self.assertEqual(response.status_code, 200)

    def test_change_view(self):
        feature = Feature.objects.create(name='test', enabled=True)
        response = self.client.get(reverse('admin:configuration_feature_change', args=(feature.pk,)))
        self.assertEqual(response.status_code, 200)
