from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from ESSArch_Core.auth.models import Notification

User = get_user_model()


class MeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user', password='pass')

        self.client = APIClient()
        self.url = reverse('me')

    def test_me_logged_out(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class NotificationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user', password='pass')
        self.url = reverse('notification-list')

    def test_list_logged_out(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_set_all_seen(self):
        notifications = [
            Notification(user=self.user, level=Notification.SUCCESS, message='test', seen=False)
            for _ in range(10)
        ]
        Notification.objects.bulk_create(notifications)
        Notification.objects.create(
            user=User.objects.create(username='other_user'), level=Notification.SUCCESS, message='test', seen=False
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.post(reverse('notification-set-all-seen'))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Notification.objects.filter(user=self.user, seen=True).count(), 10)
        self.assertFalse(Notification.objects.filter(user=self.user, seen=False).exists())
        self.assertTrue(Notification.objects.filter(user__username='other_user', seen=False).exists())


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user', password='pass')

        self.client = APIClient()
        self.url = reverse('rest_login')

    def test_no_credentials(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_credentials(self):
        response = self.client.post(self.url, data={'username': 'foo', 'password': 'bar'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_credentials(self):
        response = self.client.post(self.url, data={'username': 'user', 'password': 'pass'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_inactive_user(self):
        self.user.is_active = False
        self.user.save()

        response = self.client.post(self.url, data={'username': 'user', 'password': 'pass'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LogoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('rest_logout')

    def test_logout(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
