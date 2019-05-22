"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Tools for Producer (ETP)
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

import errno
import os
import uuid

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from groups_manager.models import GroupType

from unittest import mock

from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from ESSArch_Core.auth.models import Group
from ESSArch_Core.configuration.models import ArchivePolicy, Path
from ESSArch_Core.ip.models import InformationPackage, Order, Workarea
from ESSArch_Core.profiles.models import Profile, ProfileSA, SubmissionAgreement
from ESSArch_Core.tags.models import Structure, Tag, TagStructure
from ESSArch_Core.WorkflowEngine.models import ProcessStep


class AccessTestCase(TestCase):
    def setUp(self):
        Path.objects.create(entity="access_workarea", value="")
        Path.objects.create(entity="ingest_workarea", value="")

        self.ip = InformationPackage.objects.create()

        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member
        self.org_group_type = GroupType.objects.create(label='organization')
        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, self.ip, custom_permissions=perms)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('informationpackage-access', args=[self.ip.pk])

    def test_no_valid_option_set(self):
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_valid_option_set_to_true(self):
        res = self.client.post(self.url, {'tar': False})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_already_in_workarea(self):
        Workarea.objects.create(user=self.user, ip=self.ip, type=Workarea.ACCESS)

        res = self.client.post(self.url, {'tar': True}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_state(self):
        res = self.client.post(self.url, {'tar': True})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('ip.views.ProcessStep.run')
    def test_received_ip(self, mock_step):
        self.ip.state = 'Received'
        self.ip.save()
        res = self.client.post(self.url, {'tar': True})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        mock_step.assert_called_once()

    @mock.patch('ip.views.ProcessStep.run')
    def test_archived_ip(self, mock_step):
        self.ip.archived = True
        self.ip.save()
        res = self.client.post(self.url, {'tar': True})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        mock_step.assert_called_once()


class WorkareaViewSetTestCase(TestCase):
    def setUp(self):
        Path.objects.create(entity="access_workarea", value="")
        Path.objects.create(entity="ingest_workarea", value="")

        self.url = reverse('workarea-list')

        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member
        self.org_group_type = GroupType.objects.create(label='organization')
        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_empty(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])

    def test_post(self):
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_invalid_workarea(self):
        res = self.client.get(self.url, {'workspace_type': 'non-existing-workarea'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_aip_in_workarea_without_permission_to_view_it_and_aic_view_type(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)
        Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS)

        res = self.client.get(self.url, data={'view_type': 'aic'})
        self.assertEqual(len(res.data), 0)

    def test_aip_in_workarea_without_permission_to_view_it_and_ip_view_type(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)
        Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS, read_only=False)

        res = self.client.get(self.url, data={'view_type': 'ip'})
        self.assertEqual(len(res.data), 0)

    def test_aip_in_workarea_using_aic_view_type(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)
        Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aic.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 1)
        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip.pk))
        self.assertEqual(len(res.data[0]['information_packages'][0]['workarea']), 1)

    def test_aip_in_workarea_using_ip_view_type(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)
        Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS, read_only=False)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aip.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 0)
        self.assertEqual(len(res.data[0]['workarea']), 1)

    def test_aip_in_other_users_workarea_without_permission_to_view_specific_ip_using_aic_view_type(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)

        other_user = User.objects.create(username="other")
        Workarea.objects.create(user=other_user, ip=aip, type=Workarea.ACCESS)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic'})
        self.assertEqual(
            len(res.data), 0,
            'user must not see IPs in other users workarea if they do not have permission to view the IP'
        )

    def test_aip_in_other_users_workarea_without_permission_to_view_specific_ip_using_ip_view_type(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)

        other_user = User.objects.create(username="other")
        Workarea.objects.create(user=other_user, ip=aip, type=Workarea.ACCESS)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip'})
        self.assertEqual(
            len(res.data), 0,
            'user must not see IPs in other users workarea if they do not have permission to view the IP'
        )


class AIPInMultipleUsersWorkareaTestCase(TestCase):
    def setUp(self):
        Path.objects.create(entity="access_workarea", value="")
        Path.objects.create(entity="ingest_workarea", value="")

        self.url = reverse('workarea-list')

        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member
        self.org_group_type = GroupType.objects.create(label='organization')
        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        self.aip = InformationPackage.objects.create(aic=self.aic, package_type=InformationPackage.AIP, generation=0)
        self.aip2 = InformationPackage.objects.create(aic=self.aic, package_type=InformationPackage.AIP, generation=1)

        self.other_user = User.objects.create(username="other")
        self.workarea = Workarea.objects.create(user=self.user, ip=self.aip, type=Workarea.ACCESS)
        self.other_workarea = Workarea.objects.create(user=self.other_user, ip=self.aip2, type=Workarea.ACCESS)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_without_see_all_permission_and_aic_view_type(self):
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, self.aip, custom_permissions=perms)
        self.member.assign_object(self.group, self.aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(
            len(res.data[0]['information_packages']), 1,
            'user must not see IPs in other users workarea if they do not have "see_all_in_workspaces" permission')
        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(self.aip.pk))
        self.assertEqual(len(res.data[0]['information_packages'][0]['workarea']), 1)
        self.assertEqual(res.data[0]['information_packages'][0]['workarea'][0]['id'], str(self.workarea.pk))

    def test_without_see_all_permission_and_ip_view_type(self):
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, self.aip, custom_permissions=perms)
        self.member.assign_object(self.group, self.aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip'})
        self.assertEqual(res.data[0]['id'], str(self.aip.pk))
        self.assertEqual(
            len(res.data[0]['information_packages']), 0,
            'user must not see IPs in other users workarea if they do not have "see_all_in_workspaces" permission')
        self.assertEqual(len(res.data[0]['workarea']), 1)
        self.assertEqual(res.data[0]['workarea'][0]['id'], str(self.workarea.pk))

    def test_with_permission_to_only_see_own_using_aic_view_type_and_permission_to_see_all_in_workspaces(self):
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, self.aip, custom_permissions=perms)

        permission = Permission.objects.get(codename='see_all_in_workspaces')
        self.user.user_permissions.add(permission)

        res = self.client.get(self.url, data={'view_type': 'aic'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(
            len(res.data[0]['information_packages']), 1,
            'user must not see IPs in other users workarea if they do not have permission to view the IP'
        )
        self.assertEqual(len(res.data[0]['information_packages'][0]['workarea']), 1)
        self.assertEqual(res.data[0]['information_packages'][0]['workarea'][0]['id'], str(self.workarea.pk))

    def test_with_permission_to_only_see_own_using_ip_view_type_and_permission_to_see_all_in_workspaces(self):
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, self.aip, custom_permissions=perms)

        permission = Permission.objects.get(codename='see_all_in_workspaces')
        self.user.user_permissions.add(permission)

        res = self.client.get(self.url, data={'view_type': 'ip'})
        self.assertEqual(res.data[0]['id'], str(self.aip.pk))
        self.assertEqual(
            len(res.data[0]['information_packages']), 0,
            'user must not see IPs in other users workarea if they do not have permission to view the IP'
        )
        self.assertEqual(len(res.data[0]['workarea']), 1)
        self.assertEqual(res.data[0]['workarea'][0]['id'], str(self.workarea.pk))

    def test_with_permission_to_see_both_using_aic_view_type_and_permission_to_see_all_in_workspaces(self):
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, self.aip, custom_permissions=perms)
        self.member.assign_object(self.group, self.aip2, custom_permissions=perms)

        permission = Permission.objects.get(codename='see_all_in_workspaces')
        self.user.user_permissions.add(permission)

        res = self.client.get(self.url, data={'view_type': 'aic'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(
            len(res.data[0]['information_packages']), 2,
            'user must see other users workarea if they have "see_all_in_workspaces" permission'
        )
        self.assertEqual(len(res.data[0]['information_packages'][0]['workarea']), 1)

    def test_with_permission_to_see_both_using_ip_view_type_and_permission_to_see_all_in_workspaces(self):
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, self.aip, custom_permissions=perms)
        self.member.assign_object(self.group, self.aip2, custom_permissions=perms)

        permission = Permission.objects.get(codename='see_all_in_workspaces')
        self.user.user_permissions.add(permission)

        res = self.client.get(self.url, data={'view_type': 'ip'})
        self.assertEqual(res.data[0]['id'], str(self.aip.pk))
        self.assertEqual(
            len(res.data[0]['information_packages']), 1,
            'user must see other users workarea if they have "see_all_in_workspaces" permission'
        )
        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(self.aip2.pk))
        self.assertEqual(len(res.data[0]['workarea']), 1)


class SameAIPInMultipleUsersWorkareaTestCase(TestCase):
    def setUp(self):
        Path.objects.create(entity="access_workarea", value="")
        Path.objects.create(entity="ingest_workarea", value="")

        self.url = reverse('workarea-list')

        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member
        self.org_group_type = GroupType.objects.create(label='organization')
        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        self.aip = InformationPackage.objects.create(aic=self.aic, package_type=InformationPackage.AIP, generation=0)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, self.aip, custom_permissions=perms)

        self.other_user = User.objects.create(username="other")
        self.workarea = Workarea.objects.create(user=self.user, ip=self.aip, type=Workarea.ACCESS)
        self.other_workarea = Workarea.objects.create(user=self.other_user, ip=self.aip, type=Workarea.ACCESS)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_without_see_all_permission_and_aic_view_type(self):
        res = self.client.get(self.url, data={'view_type': 'aic'})
        self.assertEqual(len(res.data[0]['information_packages'][0]['workarea']), 1)
        self.assertEqual(res.data[0]['information_packages'][0]['workarea'][0]['id'], str(self.workarea.pk))

    def test_without_see_all_permission_and_ip_view_type(self):
        res = self.client.get(self.url, data={'view_type': 'ip'})
        self.assertEqual(len(res.data[0]['workarea']), 1)
        self.assertEqual(res.data[0]['workarea'][0]['id'], str(self.workarea.pk))

    def test_aic_view_type_and_permission_to_see_all_in_workspaces(self):
        permission = Permission.objects.get(codename='see_all_in_workspaces')
        self.user.user_permissions.add(permission)

        res = self.client.get(self.url, data={'view_type': 'aic'})
        self.assertEqual(len(res.data[0]['information_packages'][0]['workarea']), 2)

    def test_ip_view_type_and_permission_to_see_all_in_workspaces(self):
        permission = Permission.objects.get(codename='see_all_in_workspaces')
        self.user.user_permissions.add(permission)

        res = self.client.get(self.url, data={'view_type': 'ip'})
        self.assertEqual(len(res.data[0]['workarea']), 2)


class WorkareaFilesViewTestCase(TestCase):
    def setUp(self):
        Path.objects.create(entity="access_workarea", value="access")
        Path.objects.create(entity="ingest_workarea", value="ingest")

        self.user = User.objects.create(username="admin", password='admin')
        self.member = self.user.essauth_member
        self.org_group_type = GroupType.objects.create(label='organization')
        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.url = reverse('workarea-files-list')

    def test_no_type_parameter(self):
        res = self.client.get(self.url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_type_parameter(self):
        res = self.client.get(self.url, {'type': 'invalidtype'})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_illegal_path(self):
        res = self.client.get(self.url, {'type': 'access', 'path': '..'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_existing_path(self):
        res = self.client.get(self.url, {'type': 'access', 'path': 'does/not/exist'})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('ip.views.list_files', return_value=Response())
    def test_existing_path(self, mock_list_files):
        path = 'does/exist'
        fullpath = os.path.join('access', self.user.username, path)

        exists = os.path.exists
        with mock.patch('ip.views.os.path.exists', side_effect=lambda x: x == fullpath or exists(x)):
            res = self.client.get(self.url, {'type': 'access', 'path': path})
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        mock_list_files.assert_called_once_with(fullpath, False, paginator=mock.ANY, request=mock.ANY)

    def test_add_to_dip_not_responsible(self):
        self.url = reverse('workarea-files-add-to-dip')
        src = 'src.txt'
        dst = 'dst.txt'
        ip = InformationPackage.objects.create(package_type=InformationPackage.DIP)

        res = self.client.post(self.url, {'type': 'access', 'src': src, 'dst': dst, 'dip': str(ip.pk)})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_file_to_dip(self):
        self.url = reverse('workarea-files-add-to-dip')

        dstdir = 'dst'
        src = 'src.txt'
        dst = 'dst.txt'

        fullpath_src = os.path.join('access', self.user.username, src)
        fullpath_dst = os.path.join(dstdir, dst)

        ip = InformationPackage.objects.create(
            object_path=dstdir,
            responsible=self.user,
            package_type=InformationPackage.DIP
        )
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)

        exists = os.path.exists
        isfile = os.path.isfile
        with mock.patch('ip.views.os.path.exists', side_effect=lambda x: x == fullpath_src or exists(x)), \
                mock.patch('ip.views.os.path.isfile', side_effect=lambda x: x == fullpath_src or isfile(x)), \
                mock.patch('ip.views.shutil.copy2') as mock_copy:

            res = self.client.post(self.url, {'type': 'access', 'src': src, 'dst': dst, 'dip': str(ip.pk)})
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            mock_copy.assert_called_once_with(fullpath_src, fullpath_dst)

    def test_add_dir_to_dip(self):
        self.url = reverse('workarea-files-add-to-dip')

        dstdir = 'dst'
        src = 'src'
        dst = 'dst'

        fullpath_src = os.path.join('access', self.user.username, src)
        fullpath_dst = os.path.join(dstdir, dst)

        ip = InformationPackage.objects.create(
            object_path=dstdir,
            responsible=self.user,
            package_type=InformationPackage.DIP
        )
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)

        exists = os.path.exists
        with mock.patch('ip.views.os.path.exists', side_effect=lambda x: x == fullpath_src or exists(x)), \
                mock.patch('ip.views.shutil.copytree') as mock_copy:

            res = self.client.post(self.url, {'type': 'access', 'src': src, 'dst': dst, 'dip': str(ip.pk)})
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            mock_copy.assert_called_once_with(fullpath_src, fullpath_dst)

    def test_overwrite_dir_to_dip(self):
        self.url = reverse('workarea-files-add-to-dip')

        dstdir = 'dst'
        src = 'src'
        dst = 'dst'

        fullpath_src = os.path.join('access', self.user.username, src)
        fullpath_dst = os.path.join(dstdir, dst)

        ip = InformationPackage.objects.create(
            object_path=dstdir,
            responsible=self.user,
            package_type=InformationPackage.DIP
        )
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)

        exists = os.path.exists
        copytree_side_effects = [OSError(errno.EEXIST, "error"), mock.DEFAULT]
        with mock.patch('ip.views.os.path.exists', side_effect=lambda x: x == fullpath_src or exists(x)), \
                mock.patch('ip.views.shutil.copytree', side_effect=copytree_side_effects) as mock_copy, \
                mock.patch('ip.views.shutil.rmtree') as mock_rmtree:

            res = self.client.post(self.url, {'type': 'access', 'src': src, 'dst': dst, 'dip': str(ip.pk)})
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            mock_rmtree.assert_called_once_with(fullpath_dst)

            copy_calls = [mock.call(fullpath_src, fullpath_dst),
                          mock.call(fullpath_src, fullpath_dst)]
            mock_copy.assert_has_calls(copy_calls)


class InformationPackageViewSetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="admin", password='admin')
        self.member = self.user.essauth_member
        self.org_group_type = GroupType.objects.create(label='organization')
        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.user.user_profile.current_organization = self.group
        self.user.user_profile.save()

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.url = reverse('informationpackage-list')

    def test_empty(self):
        res = self.client.get(self.url)
        self.assertEqual(res.data, [])

    def test_aic_view_type_aic_no_aips(self):
        InformationPackage.objects.create(package_type=InformationPackage.AIC)

        res = self.client.get(self.url, data={'view_type': 'aic'})
        self.assertEqual(len(res.data), 0)

    def test_aic_view_type_aic_no_active_aips(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        InformationPackage.objects.create(aic=aic, active=False, package_type=InformationPackage.AIP)

        res = self.client.get(self.url, data={'view_type': 'aic'})
        self.assertEqual(len(res.data), 0)

    def test_aic_view_type_with_ordering_and_filter(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip14 = InformationPackage.objects.create(aic=aic, generation=4, state='foo')
        aip12 = InformationPackage.objects.create(aic=aic, generation=2, state='foo')
        aip13 = InformationPackage.objects.create(aic=aic, generation=3, state='foo')
        aip11 = InformationPackage.objects.create(aic=aic, generation=1, state='foo')
        aic2 = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip2 = InformationPackage.objects.create(aic=aic2, generation=0, state='foo')
        aic3 = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip3 = InformationPackage.objects.create(aic=aic3, generation=0, state='bar')

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip11, custom_permissions=perms)
        self.member.assign_object(self.group, aip12, custom_permissions=perms)
        self.member.assign_object(self.group, aip13, custom_permissions=perms)
        self.member.assign_object(self.group, aip14, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)
        self.member.assign_object(self.group, aip3, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic', 'ordering': 'create_date', 'state': 'foo'})
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]['id'], str(aic.pk))
        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip11.pk))
        self.assertEqual(res.data[0]['information_packages'][1]['id'], str(aip12.pk))
        self.assertEqual(res.data[0]['information_packages'][2]['id'], str(aip13.pk))
        self.assertEqual(res.data[0]['information_packages'][3]['id'], str(aip14.pk))
        self.assertEqual(res.data[1]['id'], str(aic2.pk))

        res = self.client.get(self.url, data={'view_type': 'aic', 'ordering': '-create_date', 'state': 'foo'})
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]['id'], str(aic2.pk))
        self.assertEqual(res.data[1]['id'], str(aic.pk))

    def test_ip_view_type_with_ordering_and_filter(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, generation=0, state='foo')
        aic2 = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip2 = InformationPackage.objects.create(aic=aic2, generation=0, state='foo')
        aic3 = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip3 = InformationPackage.objects.create(aic=aic3, generation=0, state='bar')

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)
        self.member.assign_object(self.group, aip3, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip', 'ordering': 'create_date', 'state': 'foo'})
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]['id'], str(aip.pk))
        self.assertEqual(res.data[1]['id'], str(aip2.pk))

        res = self.client.get(self.url, data={'view_type': 'ip', 'ordering': '-create_date', 'state': 'foo'})
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]['id'], str(aip2.pk))
        self.assertEqual(res.data[1]['id'], str(aip.pk))

    def test_aic_view_type_aic_two_aips_first_inactive(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(
            aic=aic, generation=0, active=False, package_type=InformationPackage.AIP
        )
        aip2 = InformationPackage.objects.create(
            aic=aic, generation=1, active=True, package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(len(res.data[0]['information_packages']), 1)
        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip2.pk))

    def test_aic_view_type_aic_two_aips_first_inactive_with_filter(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(
            aic=aic, generation=0, active=False, package_type=InformationPackage.AIP
        )
        aip2 = InformationPackage.objects.create(
            aic=aic, generation=1, active=True, package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic', 'archived': 'false'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(len(res.data[0]['information_packages']), 1)
        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip2.pk))

    def test_aic_view_type_multiple_aic_two_aips_first_inactive_with_filter(self):
        aic = InformationPackage.objects.create(label="0", package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(
            aic=aic, generation=0, active=False, package_type=InformationPackage.AIP
        )
        aip2 = InformationPackage.objects.create(
            aic=aic, generation=1, active=True, package_type=InformationPackage.AIP
        )

        aic2 = InformationPackage.objects.create(label="1", package_type=InformationPackage.AIC)
        aip3 = InformationPackage.objects.create(
            aic=aic2, generation=0, active=False, package_type=InformationPackage.AIP
        )
        aip4 = InformationPackage.objects.create(
            aic=aic2, generation=1, active=True,
            package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)
        self.member.assign_object(self.group, aip3, custom_permissions=perms)
        self.member.assign_object(self.group, aip4, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic', 'archived': 'false', 'ordering': 'label'})
        self.assertEqual(len(res.data), 2)
        self.assertEqual(len(res.data[0]['information_packages']), 1)
        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip2.pk))

    def test_aic_view_type_aic_two_aips_last_inactive(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(
            aic=aic, generation=0, active=True, package_type=InformationPackage.AIP
        )
        aip2 = InformationPackage.objects.create(
            aic=aic, generation=1, active=False, package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(len(res.data[0]['information_packages']), 1)
        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip.pk))

    def test_aic_view_type_aic_multiple_aips_one_in_workarea(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP)
        aip2 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        Path.objects.create(entity='access_workarea', value='access')
        Workarea.objects.create(user=self.user, ip=aip2, type=Workarea.ACCESS, read_only=False)

        res = self.client.get(self.url, data={'view_type': 'aic'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aic.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 1)

    def test_aic_view_type_aic_multiple_aips(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP)
        aip2 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic'})

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aic.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 2)

    def test_aic_view_type_aic_multiple_aips_same_state_empty_filter(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(
            generation=0, state='foo', aic=aic, package_type=InformationPackage.AIP
        )
        aip2 = InformationPackage.objects.create(
            generation=1, state='foo', aic=aic, package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic', 'state': ''})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aic.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 2)

        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip.pk))
        self.assertEqual(res.data[0]['information_packages'][1]['id'], str(aip2.pk))

    def test_aic_view_type_aic_multiple_aips_filter_responsible(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(
            generation=0, state='foo', aic=aic, package_type=InformationPackage.AIP
        )
        aip2 = InformationPackage.objects.create(
            responsible=self.user, generation=1, state='foo', aic=aic, package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic', 'responsible': self.user.username})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aic.pk))

        self.assertEqual(len(res.data[0]['information_packages']), 1)
        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip2.pk))

    def test_aic_view_type_aic_multiple_aips_same_state_filter_state(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(
            generation=0, state='foo', aic=aic, package_type=InformationPackage.AIP
        )
        aip2 = InformationPackage.objects.create(
            generation=1, state='foo', aic=aic, package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic', 'state': 'foo'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aic.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 2)
        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip.pk))

    def test_aic_view_type_aic_multiple_aips_different_states_filter_state(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(state='foo', aic=aic, package_type=InformationPackage.AIP)
        aip2 = InformationPackage.objects.create(state='bar', aic=aic, package_type=InformationPackage.AIP)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic', 'state': 'foo'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aic.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 1)

    def test_ip_view_type_aic_no_aips(self):
        InformationPackage.objects.create(package_type=InformationPackage.AIC)

        res = self.client.get(self.url, data={'view_type': 'ip'})
        self.assertEqual(len(res.data), 0)

    def test_ip_view_type_aic_multiple_aips(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(generation=0, aic=aic, package_type=InformationPackage.AIP)
        aip2 = InformationPackage.objects.create(generation=1, aic=aic, package_type=InformationPackage.AIP)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aip.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 1)
        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip2.pk))

    def test_ip_view_type_aic_multiple_aips_same_state_filter_state(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(
            generation=0, state='foo', aic=aic, package_type=InformationPackage.AIP
        )
        aip2 = InformationPackage.objects.create(
            generation=1, state='foo', aic=aic, package_type=InformationPackage.AIP
        )
        aip3 = InformationPackage.objects.create(
            generation=2, state='foo', aic=aic, package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)
        self.member.assign_object(self.group, aip3, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip', 'state': 'foo'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aip.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 2)
        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip2.pk))
        self.assertEqual(res.data[0]['information_packages'][1]['id'], str(aip3.pk))

    def test_ip_view_type_aic_multiple_aips_last_only_active_previous_archived_filter_archived(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(
            generation=0, active=False, aic=aic, package_type=InformationPackage.AIP
        )
        aip2 = InformationPackage.objects.create(
            generation=1, archived=True, active=False, aic=aic, package_type=InformationPackage.AIP
        )
        aip3 = InformationPackage.objects.create(
            generation=2, active=True, aic=aic, package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)
        self.member.assign_object(self.group, aip3, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip', 'archived': 'true'})
        self.assertEqual(len(res.data), 0)

    def test_ip_view_type_aic_multiple_aips_different_states_first_ip_filter_state(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(
            generation=0, state='bar', aic=aic, package_type=InformationPackage.AIP
        )
        aip2 = InformationPackage.objects.create(
            generation=1, state='foo', aic=aic, package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip', 'state': 'foo'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aip2.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 0)

    def test_ip_view_type_aic_multiple_aips_different_states_all_filter_state(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(
            generation=0, state='bar', aic=aic, package_type=InformationPackage.AIP
        )
        aip2 = InformationPackage.objects.create(
            generation=1, state='baz', aic=aic, package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip', 'state': 'foo'})
        self.assertEqual(len(res.data), 0)

    def test_aic_view_type_aic_multiple_aips_different_labels_filter_label(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(
            generation=0, state='foo', aic=aic, package_type=InformationPackage.AIP
        )
        aip2 = InformationPackage.objects.create(
            generation=1, state='bar', aic=aic, package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic', 'state': 'foo'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aic.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 1)
        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip.pk))

    def test_aic_view_type_aic_multiple_aics_different_set_of_generations(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(generation=0, aic=aic, package_type=InformationPackage.AIP)
        aip2 = InformationPackage.objects.create(generation=1, aic=aic, package_type=InformationPackage.AIP)

        aic2 = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip3 = InformationPackage.objects.create(generation=1, aic=aic2, package_type=InformationPackage.AIP)
        aip4 = InformationPackage.objects.create(generation=2, aic=aic2, package_type=InformationPackage.AIP)
        aip5 = InformationPackage.objects.create(
            generation=3, active=False, aic=aic2, package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)
        self.member.assign_object(self.group, aip3, custom_permissions=perms)
        self.member.assign_object(self.group, aip4, custom_permissions=perms)
        self.member.assign_object(self.group, aip5, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic', 'ordering': 'create_date'})
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]['id'], str(aic.pk))

        self.assertEqual(res.data[0]['information_packages'][0]['first_generation'], True)
        self.assertEqual(res.data[0]['information_packages'][0]['last_generation'], False)
        self.assertEqual(res.data[0]['information_packages'][1]['first_generation'], False)
        self.assertEqual(res.data[0]['information_packages'][1]['last_generation'], True)

        self.assertEqual(len(res.data[1]['information_packages']), 2)
        self.assertEqual(res.data[1]['information_packages'][0]['first_generation'], True)
        self.assertEqual(res.data[1]['information_packages'][0]['last_generation'], False)
        self.assertEqual(res.data[1]['information_packages'][1]['first_generation'], False)
        self.assertEqual(res.data[1]['information_packages'][1]['last_generation'], False)

    def test_ip_view_type_aic_multiple_aips_different_states_filter_state(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(
            generation=0,
            state='foo',
            aic=aic,
            package_type=InformationPackage.AIP
        )
        aip2 = InformationPackage.objects.create(
            generation=1,
            state='bar',
            aic=aic,
            package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip', 'state': 'foo'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aip.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 0)

        res = self.client.get(self.url, data={'view_type': 'ip', 'state': 'bar'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aip2.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 0)

    def test_ip_view_type_aic_multiple_aips_different_labels_all_filter_label(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(
            generation=0, state='bar', aic=aic, package_type=InformationPackage.AIP
        )
        aip2 = InformationPackage.objects.create(
            generation=1, state='baz', aic=aic, package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip', 'state': 'foo'})
        self.assertEqual(len(res.data), 0)

    def test_aic_view_type_aic_multiple_aips_different_labels_global_search(self):
        aic1 = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip11 = InformationPackage.objects.create(
            generation=0, label='first1', aic=aic1, package_type=InformationPackage.AIP
        )
        aip12 = InformationPackage.objects.create(
            generation=1, label='first2', aic=aic1, package_type=InformationPackage.AIP
        )

        aic2 = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip21 = InformationPackage.objects.create(
            generation=0, label='second1', aic=aic2, package_type=InformationPackage.AIP
        )
        aip22 = InformationPackage.objects.create(
            generation=1, label='second2', aic=aic2, package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip11, custom_permissions=perms)
        self.member.assign_object(self.group, aip12, custom_permissions=perms)
        self.member.assign_object(self.group, aip21, custom_permissions=perms)
        self.member.assign_object(self.group, aip22, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic', 'search': 'first'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aic1.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 2)
        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip11.pk))
        self.assertEqual(res.data[0]['information_packages'][1]['id'], str(aip12.pk))

    def test_ip_view_type_aic_multiple_aips_different_labels_global_search(self):
        aic1 = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip11 = InformationPackage.objects.create(
            generation=0, label='first1', aic=aic1, package_type=InformationPackage.AIP
        )
        aip12 = InformationPackage.objects.create(
            generation=1, label='first2', aic=aic1, package_type=InformationPackage.AIP
        )

        aic2 = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip21 = InformationPackage.objects.create(
            generation=0, label='second1', aic=aic2, package_type=InformationPackage.AIP
        )
        aip22 = InformationPackage.objects.create(
            generation=1, label='second2', aic=aic2, package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip11, custom_permissions=perms)
        self.member.assign_object(self.group, aip12, custom_permissions=perms)
        self.member.assign_object(self.group, aip21, custom_permissions=perms)
        self.member.assign_object(self.group, aip22, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip', 'search': 'first'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aip11.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 1)
        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip12.pk))

    def test_ip_view_type_aic_multiple_aips_different_labels_global_search_and_state(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(
            generation=0, label='foo', state='first', aic=aic, package_type=InformationPackage.AIP
        )
        aip2 = InformationPackage.objects.create(
            generation=1, label='bar', state='second', aic=aic, package_type=InformationPackage.AIP
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip', 'search': 'bar', 'state': 'second'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aip2.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 0)

    def test_aic_view_type_aic_aips_different_labels_same_aic_global_search(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(
            label='first', package_type=InformationPackage.AIP, aic=aic, generation=0
        )
        aip2 = InformationPackage.objects.create(
            label='second', package_type=InformationPackage.AIP, aic=aic, generation=1
        )

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)

        res = self.client.get(self.url, {'view_type': 'aic', 'search': 'first'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]['id'], str(aic.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 1)
        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip.pk))

    def test_aic_view_type_dip(self):
        dip = InformationPackage.objects.create(package_type=InformationPackage.DIP, generation=0)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, dip, custom_permissions=perms)

        res = self.client.get(self.url, {'view_type': 'aic'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(dip.pk))

    def test_ip_view_type_dip(self):
        dip = InformationPackage.objects.create(package_type=InformationPackage.DIP)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, dip, custom_permissions=perms)

        res = self.client.get(self.url, {'view_type': 'ip'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(dip.pk))

    def test_aic_view_type_detail_aip(self):
        aip = InformationPackage.objects.create(package_type=InformationPackage.AIP)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)

        url = reverse('informationpackage-detail', args=(str(aip.pk),))
        res = self.client.get(url, {'view_type': 'aic'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_ip_view_type_detail_aip(self):
        aip = InformationPackage.objects.create(package_type=InformationPackage.AIP)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)

        url = reverse('informationpackage-detail', args=(str(aip.pk),))
        res = self.client.get(url, {'view_type': 'ip'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_aic_view_type_detail_aip_multiple_workarea_entries(self):
        aip = InformationPackage.objects.create(package_type=InformationPackage.AIP)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)

        other_user = User.objects.create(username="other")
        Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS)
        Workarea.objects.create(user=other_user, ip=aip, type=Workarea.ACCESS)

        url = reverse('informationpackage-detail', args=(str(aip.pk),))
        res = self.client.get(url, {'view_type': 'aic'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_ip_view_type_detail_aip_multiple_workarea_entries(self):
        aip = InformationPackage.objects.create(package_type=InformationPackage.AIP)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)

        other_user = User.objects.create(username="other")
        Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS)
        Workarea.objects.create(user=other_user, ip=aip, type=Workarea.ACCESS)

        url = reverse('informationpackage-detail', args=(str(aip.pk),))
        res = self.client.get(url, {'view_type': 'ip'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_aic_view_type_aip_other_user_same_organization(self):
        member2 = User.objects.create(username="another").essauth_member
        self.group.add_member(member2)

        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP)

        perms = {'group': ['view_informationpackage']}
        member2.assign_object(self.group, aip, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic'})

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aic.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 1)

    def test_aic_view_type_aip_other_user_other_organization(self):
        member2 = User.objects.create(username="another").essauth_member
        group2 = Group.objects.create(name='organization2', group_type=self.org_group_type)
        group2.add_member(member2)

        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP)

        perms = {'group': ['view_informationpackage']}
        member2.assign_object(group2, aip, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic'})

        self.assertEqual(len(res.data), 0)

    def test_ip_view_type_aip_other_user_same_organization(self):
        member2 = User.objects.create(username="another").essauth_member
        self.group.add_member(member2)

        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)

        perms = {'group': ['view_informationpackage']}
        member2.assign_object(self.group, aip, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip'})

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aip.pk))

    def test_ip_view_type_aip_other_user_other_organization(self):
        member2 = User.objects.create(username="another").essauth_member
        group2 = Group.objects.create(name='organization2', group_type=self.org_group_type)
        group2.add_member(member2)

        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)

        perms = {'group': ['view_informationpackage']}
        member2.assign_object(group2, aip, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip'})

        self.assertEqual(len(res.data), 0)

    @mock.patch('ip.views.ProcessStep.run')
    def test_delete_ip(self, mock_step):
        cache = Path.objects.create(entity='cache', value='cache')
        ingest = Path.objects.create(entity='ingest', value='ingest')
        policy = ArchivePolicy.objects.create(cache_storage=cache, ingest_path=ingest)

        ip = InformationPackage.objects.create(object_path='foo', policy=policy)
        url = reverse('informationpackage-detail', args=(str(ip.pk),))

        # no permission
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        # view permission
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # delete permission
        perms = {'group': ['view_informationpackage', 'delete_informationpackage']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        mock_step.assert_called_once()

    def test_delete_archived_ip(self):
        ip = InformationPackage.objects.create(object_path='foo', responsible=self.user, archived=True)
        url = reverse('informationpackage-detail', args=(str(ip.pk),))
        res = self.client.delete(url)

        # no permission
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        # view permission
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # delete permission
        perms = {'group': ['view_informationpackage', 'delete_informationpackage']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # delete archived permission
        perms = {'group': ['view_informationpackage', 'delete_informationpackage', 'delete_archived']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    @mock.patch('workflow.tasks.PrepareDIP.run', side_effect=lambda *args, **kwargs: None)
    def test_prepare_dip_no_label(self, mock_prepare):
        self.url = self.url + 'prepare-dip/'
        res = self.client.post(self.url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        mock_prepare.assert_not_called()

    @mock.patch('workflow.tasks.PrepareDIP.run', side_effect=lambda *args, **kwargs: None)
    def test_prepare_dip_no_object_identifier_value(self, mock_prepare):
        self.url = self.url + 'prepare-dip/'
        self.client.post(self.url, {'label': 'foo'})

        mock_prepare.assert_called_once_with(label='foo', object_identifier_value=None, orders=[])

    @mock.patch('workflow.tasks.PrepareDIP.run', side_effect=lambda *args, **kwargs: None)
    def test_prepare_dip_with_object_identifier_value(self, mock_prepare):
        self.url = self.url + 'prepare-dip/'
        self.client.post(self.url, {'label': 'foo', 'object_identifier_value': 'bar'})

        mock_prepare.assert_called_once_with(label='foo', object_identifier_value='bar', orders=[])

    @mock.patch('workflow.tasks.PrepareDIP.run', side_effect=lambda *args, **kwargs: None)
    def test_prepare_dip_with_existing_object_identifier_value(self, mock_prepare):
        self.url = self.url + 'prepare-dip/'

        InformationPackage.objects.create(object_identifier_value='bar')
        self.client.post(self.url, {'label': 'foo', 'object_identifier_value': 'bar'})

        mock_prepare.assert_not_called()

    @mock.patch('workflow.tasks.PrepareDIP.run', side_effect=lambda *args, **kwargs: None)
    def test_prepare_dip_with_orders(self, mock_prepare):
        self.url = self.url + 'prepare-dip/'

        orders = [str(Order.objects.create(responsible=self.user).pk)]
        self.client.post(self.url, {'label': 'foo', 'orders': orders}, format='json')

        mock_prepare.assert_called_once_with(label='foo', object_identifier_value=None, orders=orders)

    @mock.patch('workflow.tasks.PrepareDIP.run', side_effect=lambda *args, **kwargs: None)
    def test_prepare_dip_with_non_existing_order(self, mock_prepare):
        self.url = self.url + 'prepare-dip/'

        orders = [str(Order.objects.create(responsible=self.user).pk), str(uuid.uuid4())]
        self.client.post(self.url, {'label': 'foo', 'orders': orders}, format='json')

        mock_prepare.assert_not_called()

    @mock.patch('workflow.tasks.ProcessStep.run', side_effect=lambda *args, **kwargs: None)
    def test_preserve_aip(self, mock_step):
        self.ip = InformationPackage.objects.create(package_type=InformationPackage.AIP)
        self.url = reverse('informationpackage-detail', args=(self.ip.pk,))
        self.url = self.url + 'preserve/'

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, self.ip, custom_permissions=perms)

        self.client.post(self.url)
        mock_step.assert_called_once()

        self.assertTrue(ProcessStep.objects.filter(information_package=self.ip).exists())

    @mock.patch('workflow.tasks.ProcessStep.run', side_effect=lambda *args, **kwargs: None)
    def test_preserve_dip(self, mock_step):
        cache = Path.objects.create(entity='cache', value='cache')
        ingest = Path.objects.create(entity='ingest', value='ingest')
        policy = ArchivePolicy.objects.create(cache_storage=cache, ingest_path=ingest)

        self.ip = InformationPackage.objects.create(package_type=InformationPackage.DIP)
        self.url = reverse('informationpackage-detail', args=(self.ip.pk,))
        self.url = self.url + 'preserve/'

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, self.ip, custom_permissions=perms)

        self.client.post(self.url, {'policy': str(policy.pk)})
        mock_step.assert_called_once()

        self.assertTrue(ProcessStep.objects.filter(information_package=self.ip).exists())


class InformationPackageReceptionViewSetTestCase(TestCase):
    def setUp(self):
        self.cache = Path.objects.create(entity='cache', value='cache')
        self.ingest = Path.objects.create(entity='ingest', value='ingest')

        self.user = User.objects.create(username="admin", password='admin')
        self.policy = ArchivePolicy.objects.create(cache_storage=self.cache, ingest_path=self.ingest)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.member = self.user.essauth_member
        self.org_group_type = GroupType.objects.create(label='organization')
        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.url = reverse('ip-reception-list')

        Path.objects.create(entity='reception', value='reception')

        self.sa = SubmissionAgreement.objects.create()
        aip_profile = Profile.objects.create(profile_type='aip')
        ProfileSA.objects.create(submission_agreement=self.sa, profile=aip_profile)

    def test_receive_without_permission(self):
        ip = InformationPackage.objects.create()
        url = reverse('ip-reception-receive', args=[ip.pk])
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)

        # return 403 when user doesn't have ip.receive permission
        res = self.client.post(url, data={})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_receive_ip_with_wrong_state(self):
        ip = InformationPackage.objects.create()
        url = reverse('ip-reception-receive', args=[ip.pk])
        perms = {'group': ['view_informationpackage', 'ip.receive']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)

        # return 404 when IP is not in state Prepared
        self.member.assign_object(self.group, ip, custom_permissions=perms)
        res = self.client.post(url, data={})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_receive_ip_with_incorrect_package_type(self):
        ip = InformationPackage.objects.create(state='Prepared')
        url = reverse('ip-reception-receive', args=[ip.pk])
        perms = {'group': ['view_informationpackage', 'ip.receive']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)

        # return 404 when IP is not of type AIP
        res = self.client.post(url, data={})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_receive_ip_with_missing_files(self):
        ip = InformationPackage.objects.create(state='Prepared', package_type=InformationPackage.AIP)
        url = reverse('ip-reception-receive', args=[ip.pk])
        perms = {'group': ['view_informationpackage', 'ip.receive']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)

        # return 400 when any of the files doesn't exist
        ip.package_type = InformationPackage.AIP
        ip.save()
        res = self.client.post(url, data={})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('ip.views.InformationPackageReceptionViewSet.get_container_for_xml', return_value='foo.tar')
    @mock.patch('ip.views.os.path.isfile', return_value=True)
    def test_receive_ip_with_missing_policy(self, mock_isfile, mock_get_container):
        ip = InformationPackage.objects.create(state='Prepared', package_type=InformationPackage.AIP)
        url = reverse('ip-reception-receive', args=[ip.pk])
        perms = {'group': ['view_informationpackage', 'ip.receive']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)

        # return 400 when invalid or no policy is provided
        res = self.client.post(url, data={})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('ip.views.InformationPackageReceptionViewSet.get_container_for_xml', return_value='foo.tar')
    @mock.patch('ip.views.os.path.isfile', return_value=True)
    def test_receive_ip_with_missing_tag(self, mock_isfile, mock_get_container):
        ip = InformationPackage.objects.create(state='Prepared', package_type=InformationPackage.AIP)
        url = reverse('ip-reception-receive', args=[ip.pk])
        perms = {'group': ['view_informationpackage', 'ip.receive']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)

        # return 400 when no tag is provided
        res = self.client.post(url, data={'archive_policy': self.policy.pk})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('ip.views.InformationPackageReceptionViewSet.get_container_for_xml', return_value='foo.tar')
    @mock.patch('ip.views.os.path.isfile', return_value=True)
    @mock.patch('ip.views.ProcessStep.run', side_effect=lambda *args, **kwargs: None)
    def test_receive_ip_with_correct_data(self, mock_receive, mock_isfile, mock_get_container):
        ip = InformationPackage.objects.create(state='Prepared', package_type=InformationPackage.AIP)
        url = reverse('ip-reception-receive', args=[ip.pk])
        perms = {'group': ['view_informationpackage', 'ip.receive']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)

        tag = Tag.objects.create()
        structure = Structure.objects.create()
        tag_structure = TagStructure.objects.create(tag=tag, structure=structure)
        res = self.client.post(url, data={'archive_policy': self.policy.pk, 'tag': tag_structure.pk})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        mock_receive.assert_called_once()

    def test_prepare_conflict(self):
        ip = InformationPackage.objects.create(object_identifier_value='foo')
        url = reverse('ip-reception-prepare', args=[ip.object_identifier_value])
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    def test_prepare_missing_package(self):
        url = reverse('ip-reception-prepare', args=[123])
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('ip.views.parse_submit_description', return_value={})
    @mock.patch('ip.views.InformationPackageReceptionViewSet.get_container_for_xml', return_value='foo.tar')
    @mock.patch('ip.views.os.path.isfile', return_value=True)
    def test_prepare_without_sa(self, mock_isfile, mock_get_container, mock_parse_sd):
        url = reverse('ip-reception-prepare', args=[123])
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('ip.views.parse_submit_description')
    @mock.patch('ip.views.InformationPackageReceptionViewSet.get_container_for_xml', return_value='foo.tar')
    @mock.patch('ip.views.os.path.isfile', return_value=True)
    def test_prepare_with_invalid_sa_in_xml(self, mock_isfile, mock_get_container, mock_parse_sd):
        mock_parse_sd.return_value = {'altrecordids': {'SUBMISSIONAGREEMENT': [uuid.uuid4()]}}

        url = reverse('ip-reception-prepare', args=[123])
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('ip.views.parse_submit_description')
    @mock.patch('ip.views.InformationPackageReceptionViewSet.get_container_for_xml', return_value='foo.tar')
    @mock.patch('ip.views.os.path.isfile', return_value=True)
    def test_prepare_with_valid_sa_without_profiles_referenced_in_xml(self, mock_isfile, mock_get_container,
                                                                      mock_parse_sd):
        sa = SubmissionAgreement.objects.create()
        mock_parse_sd.return_value = {'altrecordids': {'SUBMISSIONAGREEMENT': [sa.pk]}}

        url = reverse('ip-reception-prepare', args=[123])
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('ip.views.parse_submit_description')
    @mock.patch('ip.views.InformationPackageReceptionViewSet.get_container_for_xml', return_value='foo.tar')
    @mock.patch('ip.views.os.path.isfile', return_value=True)
    def test_prepare_with_valid_sa_with_profiles_referenced_in_xml(self, mock_isfile, mock_get_container,
                                                                   mock_parse_sd):
        sa = SubmissionAgreement.objects.create(
            profile_aic_description=Profile.objects.create(),
            profile_aip=Profile.objects.create(),
            profile_aip_description=Profile.objects.create(),
            profile_dip=Profile.objects.create(),
        )
        mock_parse_sd.return_value = {'altrecordids': {'SUBMISSIONAGREEMENT': [sa.pk]}}

        url = reverse('ip-reception-prepare', args=[123])
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        ip_exists = InformationPackage.objects.filter(
            object_identifier_value='123',
            package_type=InformationPackage.AIP,
            responsible=self.user,
            submission_agreement=sa).exists()
        self.assertTrue(ip_exists)


class OrderViewSetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="admin")

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_empty(self):
        url = reverse('order-list')
        res = self.client.get(url)

        self.assertEqual(res.data, [])

    def test_list_only_owned(self):
        other_user = User.objects.create(username="user")
        order = Order.objects.create(responsible=self.user)
        Order.objects.create(responsible=other_user)

        url = reverse('order-list')
        res = self.client.get(url)

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(order.pk))

    def test_list_all_if_superuser(self):
        other_user = User.objects.create(username="user")
        Order.objects.create(responsible=self.user)
        Order.objects.create(responsible=other_user)

        self.user.is_superuser = True
        self.user.save()

        url = reverse('order-list')
        res = self.client.get(url)

        self.assertEqual(len(res.data), 2)

    def test_detail_owned(self):
        order = Order.objects.create(responsible=self.user)

        url = reverse('order-detail', args=[order.pk])
        res = self.client.get(url)

        self.assertEqual(res.data['id'], str(order.pk))

    def test_detail_non_existing(self):
        url = reverse('order-detail', args=[uuid.uuid4()])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_deny_detail_other(self):
        other_user = User.objects.create(username="user")
        order = Order.objects.create(responsible=other_user)

        url = reverse('order-detail', args=[order.pk])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_other_super_user(self):
        other_user = User.objects.create(username="user")
        order = Order.objects.create(responsible=other_user)

        self.user.is_superuser = True
        self.user.save()

        url = reverse('order-detail', args=[order.pk])
        res = self.client.get(url)

        self.assertEqual(res.data['id'], str(order.pk))

    def test_create_without_ip(self):
        url = reverse('order-list')
        res = self.client.post(url, {'label': 'foo'})

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['label'], 'foo')
        self.assertTrue(Order.objects.filter(label='foo', responsible=self.user).exists())

    def test_create_with_dip(self):
        url = reverse('order-list')
        ip = InformationPackage.objects.create(package_type=InformationPackage.DIP)
        ip_url = reverse('informationpackage-detail', args=[ip.pk])
        res = self.client.post(url, {'label': 'foo', 'information_packages': [ip_url]})

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.first().information_packages.first(), ip)

    def test_create_with_ip_other_than_dip(self):
        url = reverse('order-list')
        ip = InformationPackage.objects.create(package_type=InformationPackage.SIP)
        ip_url = reverse('informationpackage-detail', args=[ip.pk])
        res = self.client.post(url, {'label': 'foo', 'information_packages': [ip_url]})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
