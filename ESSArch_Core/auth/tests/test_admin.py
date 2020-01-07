from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ESSArch_Core.auth.models import ProxyGroup


class UserAdminTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(is_staff=True, is_superuser=True)

    def setUp(self):
        self.client.force_login(self.user)

    def test_add_view(self):
        response = self.client.get(reverse('admin:essauth_proxyuser_add'))
        self.assertEqual(response.status_code, 200)

    def test_changelist_view(self):
        response = self.client.get(reverse('admin:essauth_proxyuser_changelist'))
        self.assertEqual(response.status_code, 200)

    def test_change_view(self):
        response = self.client.get(reverse('admin:essauth_proxyuser_change', args=(self.user.pk,)))
        self.assertEqual(response.status_code, 200)


class GroupAdminTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(is_staff=True, is_superuser=True)

    def setUp(self):
        self.client.force_login(self.user)

    def test_add_view(self):
        response = self.client.get(reverse('admin:essauth_proxygroup_add'))
        self.assertEqual(response.status_code, 200)

    def test_changelist_view(self):
        response = self.client.get(reverse('admin:essauth_proxygroup_changelist'))
        self.assertEqual(response.status_code, 200)

    def test_change_view(self):
        grp = ProxyGroup.objects.create()
        response = self.client.get(reverse('admin:essauth_proxygroup_change', args=(grp.pk,)))
        self.assertEqual(response.status_code, 200)
