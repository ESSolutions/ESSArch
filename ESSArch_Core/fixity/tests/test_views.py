import os
import shutil
import tempfile

from celery import states as celery_states
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.fixity.checksum import calculate_checksum
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.testing.runner import TaskRunner
from ESSArch_Core.WorkflowEngine.models import ProcessTask

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

    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

        Path.objects.create(entity='temp', value=tempfile.mkdtemp(dir=self.datadir))

    def test_without_permission(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @TaskRunner(False)
    def test_create_and_run_workflow(self):
        self.client.force_authenticate(self.superuser)

        ip = InformationPackage.objects.create(
            object_path=tempfile.mkdtemp(dir=self.datadir),
        )
        os.makedirs(os.path.join(ip.object_path, 'content'))

        with open(os.path.join(ip.object_path, 'content', 'foo.txt'), 'w') as f:
            f.write('hello')

        expected = calculate_checksum(os.path.join(ip.object_path, 'content', 'foo.txt'), 'SHA-224')

        with self.subTest('invalid file path'):
            response = self.client.post(self.url, {
                'information_package': str(ip.pk),
                'validators': [
                    {
                        'name': 'checksum',
                        'path': 'foo.txt',
                        'context': 'checksum_str',
                        'options': {
                            'expected': expected,
                            'algorithm': 'SHA-224',
                        }
                    },
                ],
            })
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertFalse(ProcessTask.objects.exists())

        with self.subTest('valid path and expected value'):
            response = self.client.post(self.url, {
                'information_package': str(ip.pk),
                'validators': [
                    {
                        'name': 'checksum',
                        'path': 'content/foo.txt',
                        'context': 'checksum_str',
                        'options': {
                            'expected': expected,
                            'algorithm': 'SHA-224',
                        }
                    },
                ],
            })
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(ProcessTask.objects.filter(status=celery_states.SUCCESS).count(), 1)
            self.assertEqual(ProcessTask.objects.filter(status=celery_states.FAILURE).count(), 0)

        with self.subTest('valid path and unexpected value'):
            response = self.client.post(self.url, {
                'information_package': str(ip.pk),
                'validators': [
                    {
                        'name': 'checksum',
                        'path': 'content/foo.txt',
                        'context': 'checksum_str',
                        'options': {
                            'expected': 'incorrect',
                            'algorithm': 'SHA-224',
                        }
                    },
                ],
            })
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(ProcessTask.objects.filter(status=celery_states.SUCCESS).count(), 1)
            self.assertEqual(ProcessTask.objects.filter(status=celery_states.FAILURE).count(), 1)
