"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Core
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import os
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from groups_manager.models import Group, GroupMember, GroupType, Member
from groups_manager.utils import get_permission_name

from guardian.shortcuts import assign_perm

from rest_framework import status
from rest_framework.test import APIClient

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.ip.models import InformationPackage, Workarea
from ESSArch_Core.util import timestamp_to_datetime

User = get_user_model()

class InformationPackageManagerTestCase(TestCase):
    def setUp(self):
        self.org_group_type = GroupType.objects.create(label='organization')
        self.user = User.objects.create(username="admin")
        self.member = Member.objects.create(username=self.user.username, django_user=self.user)

    def test_visible_to_user_no_ips_created(self):
        self.assertFalse(InformationPackage.objects.visible_to_user(self.user).exists())

    def test_visible_to_user_ip_without_permission(self):
        InformationPackage.objects.create()
        self.assertFalse(InformationPackage.objects.visible_to_user(self.user).exists())

    def test_visible_to_user_ip_with_permission_added_to_user(self):
        ip = InformationPackage.objects.create()

        perm_name = get_permission_name('view_informationpackage', ip)
        assign_perm(perm_name, self.user, ip)

        self.assertTrue(InformationPackage.objects.visible_to_user(self.user).exists())

    def test_visible_to_user_ip_with_permission_added_to_organization(self):
        ip = InformationPackage.objects.create()

        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group.add_member(self.member)
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(group, ip, custom_permissions=perms)

        self.assertTrue(InformationPackage.objects.visible_to_user(self.user).exists())

    def test_visible_to_user_ip_with_permission_added_to_nested_group(self):
        ip = InformationPackage.objects.create()

        org = Group.objects.create(name='organization', group_type=self.org_group_type)
        group = Group.objects.create(name='group', parent=org)
        group.add_member(self.member)
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(group, ip, custom_permissions=perms)

        self.assertTrue(InformationPackage.objects.visible_to_user(self.user).exists())


class InformationPackageTestCase(TestCase):
    def setUp(self):
        self.bd = os.path.dirname(os.path.realpath(__file__))
        Path.objects.create(
            entity="path_mimetypes_definitionfile",
            value=os.path.join(self.bd, "mime.types")
        )

        self.datadir = tempfile.mkdtemp()
        self.ip = InformationPackage.objects.create(object_path=self.datadir)

    def tearDown(self):
        try:
            shutil.rmtree(self.datadir)
        except:
            pass

    def test_list_file(self):
        _, path = tempfile.mkstemp(dir=self.datadir)
        self.assertEqual(self.ip.files().data, [{'type': 'file', 'name': os.path.basename(path), 'size': 0, 'modified': timestamp_to_datetime(os.stat(path).st_mtime)}])

    def test_list_folder(self):
        path = tempfile.mkdtemp(dir=self.datadir)
        self.assertEqual(self.ip.files().data, [{'type': 'dir', 'name': os.path.basename(path), 'size': 0, 'modified': timestamp_to_datetime(os.stat(path).st_mtime)}])

    def test_list_folder_content(self):
        path = tempfile.mkdtemp(dir=self.datadir)
        _, filepath = tempfile.mkstemp(dir=path)
        self.assertEqual(self.ip.files(path=path).data, [{'type': 'file', 'name': os.path.basename(filepath), 'size': os.stat(filepath).st_size, 'modified': timestamp_to_datetime(os.stat(filepath).st_mtime)}])


class WorkareaEntryViewSetTestCase(TestCase):
    def setUp(self):
        Path.objects.create(entity="access_workarea", value="")
        Path.objects.create(entity="ingest_workarea", value="")

        self.url = reverse('workarea-entries-list')

        self.user = User.objects.create(username="admin")
        self.member = Member.objects.create(username=self.user.username, django_user=self.user)
        self.org_group_type = GroupType.objects.create(label='organization')
        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

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

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)

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

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)

        res = self.client.get(self.url)
        self.assertEqual(len(res.data), 0)

    def test_aip_in_other_users_workarea_with_permission_to_see_all_in_workspaces(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)

        other_user = User.objects.create(username="other")
        Workarea.objects.create(user=other_user, ip=aip, type=Workarea.ACCESS)

        permission = Permission.objects.get(codename='see_all_in_workspaces')
        self.user.user_permissions.add(permission)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)

        res = self.client.get(self.url)
        self.assertEqual(len(res.data), 1)

    def test_delete_aip_in_read_only_workarea(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)

        workarea = Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)

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

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)

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

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)

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

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)

        permission = Permission.objects.get(codename='see_all_in_workspaces')
        self.user.user_permissions.add(permission)

        url = reverse('workarea-entries-detail', args=(str(workarea.pk),))
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        try:
            aip.refresh_from_db()
        except InformationPackage.DoesNotExist:
            self.fail("IP should not be deleted when other users read only workarea is deleted")

    def test_aip_in_other_users_workarea_with_permission_to_see_all_in_workspaces(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)

        other_user = User.objects.create(username="other")
        Workarea.objects.create(user=other_user, ip=aip, type=Workarea.ACCESS)

        permission = Permission.objects.get(codename='see_all_in_workspaces')
        self.user.user_permissions.add(permission)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)

        res = self.client.get(self.url)
        self.assertEqual(len(res.data), 1)
