from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from ESSArch_Core.auth.models import ProxyGroup

User = get_user_model()


class UserAdminTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(is_staff=True)
        self.ctype = ContentType.objects.get_for_model(User)

        self.client.force_login(self.user)

    def test_add_view(self):
        # Django requires both add and change permissions for adding users
        self.user.user_permissions.add(
            Permission.objects.get(content_type=self.ctype, codename='add_user'),
            Permission.objects.get(content_type=self.ctype, codename='change_user'),
        )
        response = self.client.get(reverse('admin:essauth_proxyuser_add'))
        self.assertEqual(response.status_code, 200)

    def test_changelist_view(self):
        self.user.user_permissions.add(
            Permission.objects.get(content_type=self.ctype, codename='view_user'),
        )
        response = self.client.get(reverse('admin:essauth_proxyuser_changelist'))
        self.assertEqual(response.status_code, 200)

    def test_change_view(self):
        self.user.user_permissions.add(
            Permission.objects.get(content_type=self.ctype, codename='change_user'),
        )
        response = self.client.get(reverse('admin:essauth_proxyuser_change', args=(self.user.pk,)))
        self.assertNotContains(response, 'Assigned roles', status_code=200)

        self.user.user_permissions.add(
            Permission.objects.get(codename='assign_groupmemberrole'),
        )
        response = self.client.get(reverse('admin:essauth_proxyuser_change', args=(self.user.pk,)))
        self.assertContains(response, 'Assigned roles', status_code=200)

    def test_read_only_view(self):
        # fixed in django-nested-inline #110

        self.user.user_permissions.add(
            Permission.objects.get(content_type=self.ctype, codename='view_user'),
        )
        response = self.client.get(reverse('admin:essauth_proxyuser_change', args=(self.user.pk,)))
        self.assertNotContains(response, 'Assigned roles', status_code=200)


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
