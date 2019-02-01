from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from ESSArch_Core.auth.models import Group, GroupMember, GroupMemberRole, GroupType
from ESSArch_Core.configuration.models import Path
from ESSArch_Core.ip.models import InformationPackage, Workarea
from ESSArch_Core.ip.serializers import InformationPackageSerializer

User = get_user_model()


class GetAllInformationPackagesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.factory = APIRequestFactory()
        self.url = reverse('informationpackage-list')

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.org_group_type = GroupType.objects.create(label='organization')
        self.org = Group.objects.create(name='organization', group_type=self.org_group_type)

        perms = Permission.objects.filter(codename='view_informationpackage')
        self.user_role = GroupMemberRole.objects.create(codename='user_role')
        self.user_role.permissions.set(perms)

        membership = GroupMember.objects.create(member=self.member, group=self.org)
        membership.roles.add(self.user_role)

        ip = InformationPackage.objects.create()
        self.org.add_object(ip)

    def test_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        # get API response
        self.client.force_authenticate(user=self.user)
        request = self.factory.get(self.url)
        force_authenticate(request, user=self.user)
        request.user = self.user
        response = self.client.get(self.url)

        # get data from DB
        ips = InformationPackage.objects.all()
        serializer = InformationPackageSerializer(ips, many=True, context={'request': request})

        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class WorkareaEntryViewSetTestCase(TestCase):
    def setUp(self):
        Path.objects.create(entity="access_workarea", value="")
        Path.objects.create(entity="ingest_workarea", value="")

        self.url = reverse('workarea-entries-list')

        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member
        self.org_group_type = GroupType.objects.create(label='organization')
        self.org = Group.objects.create(name='organization', group_type=self.org_group_type)

        user_role = GroupMemberRole.objects.create(codename='user_role')
        perms = Permission.objects.filter(codename='view_informationpackage')
        user_role.permissions.set(perms)

        membership = GroupMember.objects.create(member=self.member, group=self.org)
        membership.roles.add(user_role)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_empty(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])

    def test_aip_in_workarea_without_permission_to_see_ip(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)
        Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS, read_only=False)

        res = self.client.get(self.url)
        self.assertEqual(len(res.data), 0)

    def test_aip_in_workarea(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)
        Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS)

        self.org.add_object(aip)

        res = self.client.get(self.url)
        self.assertEqual(len(res.data), 1)

    def test_aip_in_other_users_workarea_without_permission_to_see_ip(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)

        other_user = User.objects.create(username="other")
        Workarea.objects.create(user=other_user, ip=aip, type=Workarea.ACCESS)

        res = self.client.get(self.url)
        self.assertEqual(len(res.data), 0)

    def test_aip_in_other_users_workarea(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)

        other_user = User.objects.create(username="other")
        Workarea.objects.create(user=other_user, ip=aip, type=Workarea.ACCESS)

        self.org.add_object(aip)

        res = self.client.get(self.url)
        self.assertEqual(len(res.data), 0)

    def test_aip_in_other_users_workarea_with_permission_to_see_all_in_workspaces(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)

        other_user = User.objects.create(username="other")
        Workarea.objects.create(user=other_user, ip=aip, type=Workarea.ACCESS)

        self.org.add_object(aip)

        permission = Permission.objects.get(codename='see_all_in_workspaces')
        self.user.user_permissions.add(permission)

        res = self.client.get(self.url)
        self.assertEqual(len(res.data), 1)

    def test_delete_aip_in_read_only_workarea(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)

        workarea = Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS)

        self.org.add_object(aip)

        url = reverse('workarea-entries-detail', args=(str(workarea.pk),))
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        try:
            aip.refresh_from_db()
        except InformationPackage.DoesNotExist:
            self.fail("IP should not be deleted when read only workarea is deleted")

    def test_delete_aip_in_non_read_only_workarea(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)

        workarea = Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS, read_only=False)

        self.org.add_object(aip)

        url = reverse('workarea-entries-detail', args=(str(workarea.pk),))
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        with self.assertRaises(InformationPackage.DoesNotExist):
            aip.refresh_from_db()

    def test_delete_aip_in_other_users_workarea_without_permission(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)

        other_user = User.objects.create(username="other")
        workarea = Workarea.objects.create(user=other_user, ip=aip, type=Workarea.ACCESS)

        self.org.add_object(aip)

        url = reverse('workarea-entries-detail', args=(str(workarea.pk),))
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        try:
            workarea.refresh_from_db()
            aip.refresh_from_db()
        except Workarea.DoesNotExist:
            self.fail("Workarea should not be deleted when not allowed to see it")
        except InformationPackage.DoesNotExist:
            self.fail("IP should not be deleted when other users read only workarea is deleted")

    def test_delete_aip_in_other_users_workarea_with_permission_to_see_all_in_workspaces(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)

        other_user = User.objects.create(username="other")
        workarea = Workarea.objects.create(user=other_user, ip=aip, type=Workarea.ACCESS)

        self.org.add_object(aip)

        permission = Permission.objects.get(codename='see_all_in_workspaces')
        self.user.user_permissions.add(permission)

        url = reverse('workarea-entries-detail', args=(str(workarea.pk),))
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        try:
            aip.refresh_from_db()
        except InformationPackage.DoesNotExist:
            self.fail("IP should not be deleted when other users read only workarea is deleted")
