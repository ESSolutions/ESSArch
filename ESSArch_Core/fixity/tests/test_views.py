from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class ValidatorViewSetTests(APITestCase):
    def test_list(self):
        url = reverse('validators-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
