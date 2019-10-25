from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class StatsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='user')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        url = reverse('stats')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_export(self):
        url = reverse('stats-export')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
