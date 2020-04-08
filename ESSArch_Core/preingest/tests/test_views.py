# -*- coding: utf-8 -*-

from celery import states as celery_states
from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from ESSArch_Core.WorkflowEngine.models import ProcessTask


class ProcessTaskViewSetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="admin")

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_detail_params_with_unicode(self):
        t = ProcessTask.objects.create(params={'foo': 'åäö'})
        url = reverse('processtask-detail', args=(t.pk,))

        self.client.get(url)


class RetryTaskTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="admin")

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.task = ProcessTask.objects.create(
            name='ESSArch_Core.WorkflowEngine.tests.tasks.First',
            status=celery_states.FAILURE
        )
        self.url = reverse('processtask-retry', args=(self.task.pk,))

    def test_retry_without_permissions(self):
        res = self.client.post(self.url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_retry_with_permissions(self):
        self.user.user_permissions.add(Permission.objects.get(codename='can_retry'))
        res = self.client.post(self.url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
