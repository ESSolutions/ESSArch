from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from ESSArch_Core.configuration.models import Feature

User = get_user_model()


class FeatureTests(APITestCase):
    def test_list(self):
        url = reverse('features-list')
        Feature.objects.create(name='test', enabled=True)

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_create(self):
        url = reverse('features-list')
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class SiteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='user')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('configuration-site')

    def test_site(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class SysInfoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='user')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('configuration-sysinfo')

    def test_site(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
