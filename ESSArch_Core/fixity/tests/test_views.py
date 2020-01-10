from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.testing.runner import TaskRunner

User = get_user_model()


class ValidatorViewSetTests(APITestCase):
    def test_list(self):
        url = reverse('validators-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ValidatorWorkflowViewSetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create()
        cls.superuser = User.objects.create(username='superuser', is_superuser=True)
        cls.url = reverse('validator-workflows-list')

    def test_without_permission(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @TaskRunner()
    def test_create_and_run_workflow(self):
        self.client.force_authenticate(self.superuser)

        ip = InformationPackage.objects.create()

        response = self.client.post(self.url, {
            'information_package': str(ip.pk),
            'validators': [
                {
                    'name': 'checksum',
                }
            ],
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
