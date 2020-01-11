"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""
import errno
import filecmp
import glob
import io
import os
import shutil
import tarfile
import tempfile
import uuid
import zipfile
from datetime import datetime
from unittest import mock

from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.timezone import make_aware
from groups_manager.models import GroupType
from lxml import etree
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient, APITestCase

from ESSArch_Core.auth.models import Group, GroupMember, GroupMemberRole
from ESSArch_Core.configuration.models import EventType, Path, StoragePolicy
from ESSArch_Core.essxml.Generator.xmlGenerator import XMLGenerator
from ESSArch_Core.ip.models import (
    InformationPackage,
    Order,
    OrderType,
    Workarea,
)
from ESSArch_Core.profiles.models import (
    Profile,
    ProfileIP,
    ProfileIPData,
    SubmissionAgreement,
    SubmissionAgreementIPData,
)
from ESSArch_Core.storage.models import (
    DISK,
    STORAGE_TARGET_STATUS_ENABLED,
    StorageMedium,
    StorageMethod,
    StorageMethodTargetRelation,
    StorageObject,
    StorageTarget,
)
from ESSArch_Core.testing.runner import TaskRunner
from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask


class AccessTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Path.objects.create(entity="access_workarea", value="")
        Path.objects.create(entity="ingest_workarea", value="")
        Path.objects.create(entity='temp', value="")

        cls.org_group_type = GroupType.objects.create(label='organization')

    def setUp(self):
        cache = StorageMethod.objects.create()
        cache_target = StorageTarget.objects.create(name='cache target')

        StorageMethodTargetRelation.objects.create(
            storage_method=cache,
            storage_target=cache_target,
            status=STORAGE_TARGET_STATUS_ENABLED
        )
        storage_medium = StorageMedium.objects.create(
            storage_target=cache_target,
            status=20, location_status=50,
            block_size=1024, format=103
        )

        policy = StoragePolicy.objects.create(
            cache_storage=cache,
            ingest_path=Path.objects.create(entity='ingest', value='ingest'),
        )
        sa = SubmissionAgreement.objects.create(policy=policy)
        self.ip = InformationPackage.objects.create(submission_agreement=sa)
        self.ip.aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)

        StorageObject.objects.create(
            storage_medium=storage_medium, ip=self.ip,
            content_location_type=DISK,
        )

        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member
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

    @mock.patch('ESSArch_Core.ip.views.ProcessStep.run')
    def test_received_ip(self, mock_step):
        self.ip.state = 'Received'
        self.ip.save()
        res = self.client.post(self.url, {'tar': True})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        mock_step.assert_called_once()

    @mock.patch('ESSArch_Core.ip.views.ProcessStep.run')
    def test_archived_ip(self, mock_step):
        self.ip.archived = True
        self.ip.save()
        res = self.client.post(self.url, {'tar': True})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        mock_step.assert_called_once()


class WorkareaViewSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Path.objects.create(entity="access_workarea", value="")
        Path.objects.create(entity="ingest_workarea", value="")
        Path.objects.create(entity="temp", value="")

        cls.url = reverse('workarea-list')
        cls.org_group_type = GroupType.objects.create(label='organization')

    def setUp(self):
        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member
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
        self.group.add_object(aip)
        Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS)

        res = self.client.get(self.url, data={'view_type': 'aic'})
        self.assertEqual(len(res.data), 0)

    def test_aip_in_workarea_without_permission_to_view_it_and_ip_view_type(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)
        self.group.add_object(aip)
        Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS, read_only=False)

        res = self.client.get(self.url, data={'view_type': 'ip'})
        self.assertEqual(len(res.data), 0)

    def test_aip_in_workarea_using_aic_view_type(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)
        aip2 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=1)
        aip3 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=2)
        Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS, read_only=False)
        Workarea.objects.create(user=self.user, ip=aip2, type=Workarea.ACCESS, read_only=False)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)
        self.member.assign_object(self.group, aip3, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'aic'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aic.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 2)

        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip.pk))
        self.assertEqual(len(res.data[0]['information_packages'][0]['workarea']), 1)

        self.assertEqual(res.data[0]['information_packages'][1]['id'], str(aip2.pk))
        self.assertEqual(len(res.data[0]['information_packages'][1]['workarea']), 1)

    def test_aip_in_workarea_using_ip_view_type(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)
        aip2 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=1)
        aip3 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=2)
        Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS, read_only=False)
        Workarea.objects.create(user=self.user, ip=aip2, type=Workarea.ACCESS, read_only=False)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)
        self.member.assign_object(self.group, aip3, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip'})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(aip.pk))
        self.assertEqual(len(res.data[0]['information_packages']), 1)

        self.assertEqual(res.data[0]['information_packages'][0]['id'], str(aip2.pk))
        self.assertEqual(len(res.data[0]['workarea']), 1)

    def test_aip_in_workarea_using_flat_view_type(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=0)
        aip2 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=1)
        aip3 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=2)
        Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS, read_only=False)
        Workarea.objects.create(user=self.user, ip=aip2, type=Workarea.ACCESS, read_only=False)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)
        self.member.assign_object(self.group, aip3, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'flat'})
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]['id'], str(aip.pk))
        self.assertEqual(len(res.data[0]['workarea']), 1)

        self.assertEqual(res.data[1]['id'], str(aip2.pk))
        self.assertEqual(len(res.data[1]['workarea']), 1)

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
    @classmethod
    def setUpTestData(cls):
        Path.objects.create(entity="access_workarea", value="")
        Path.objects.create(entity="ingest_workarea", value="")
        Path.objects.create(entity="temp", value="")

        cls.url = reverse('workarea-list')
        cls.org_group_type = GroupType.objects.create(label='organization')

    def setUp(self):
        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member
        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        self.aip = InformationPackage.objects.create(aic=self.aic, package_type=InformationPackage.AIP, generation=0)
        self.aip2 = InformationPackage.objects.create(aic=self.aic, package_type=InformationPackage.AIP, generation=1)

        self.group.add_object(self.aip)
        self.group.add_object(self.aip2)

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
    @classmethod
    def setUpTestData(cls):
        Path.objects.create(entity="access_workarea", value="")
        Path.objects.create(entity="ingest_workarea", value="")
        Path.objects.create(entity="temp", value="")

        cls.url = reverse('workarea-list')
        cls.org_group_type = GroupType.objects.create(label='organization')

    def setUp(self):
        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member
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
    @classmethod
    def setUpTestData(cls):
        Path.objects.create(entity="access_workarea", value="access")
        Path.objects.create(entity="ingest_workarea", value="ingest")

        cls.url = reverse('workarea-files-list')
        cls.org_group_type = GroupType.objects.create(label='organization')

    def setUp(self):
        self.user = User.objects.create(username="admin", password='admin')
        self.member = self.user.essauth_member
        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

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

    @mock.patch('ESSArch_Core.ip.views.list_files', return_value=Response())
    def test_existing_path(self, mock_list_files):
        path = 'does/exist'
        fullpath = os.path.join('access', self.user.username, path)

        exists = os.path.exists
        with mock.patch('ESSArch_Core.ip.views.os.path.exists', side_effect=lambda x: x == fullpath or exists(x)):
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

        full_src = os.path.join('access', self.user.username, src)
        full_dst = os.path.join(dstdir, dst)

        ip = InformationPackage.objects.create(
            object_path=dstdir,
            responsible=self.user,
            package_type=InformationPackage.DIP
        )
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)

        exists = os.path.exists
        isfile = os.path.isfile
        with mock.patch('ESSArch_Core.ip.views.os.path.exists', side_effect=lambda x: x == full_src or exists(x)), \
                mock.patch('ESSArch_Core.ip.views.os.path.isfile', side_effect=lambda x: x == full_src or isfile(x)), \
                mock.patch('ESSArch_Core.ip.views.shutil.copy2') as mock_copy:

            res = self.client.post(self.url, {'type': 'access', 'src': src, 'dst': dst, 'dip': str(ip.pk)})
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            mock_copy.assert_called_once_with(full_src, full_dst)

    def test_add_dir_to_dip(self):
        self.url = reverse('workarea-files-add-to-dip')

        dstdir = 'dst'
        src = 'src'
        dst = 'dst'

        full_src = os.path.join('access', self.user.username, src)
        full_dst = os.path.join(dstdir, dst)

        ip = InformationPackage.objects.create(
            object_path=dstdir,
            responsible=self.user,
            package_type=InformationPackage.DIP
        )
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)

        exists = os.path.exists
        with mock.patch('ESSArch_Core.ip.views.os.path.exists', side_effect=lambda x: x == full_src or exists(x)), \
                mock.patch('ESSArch_Core.ip.views.shutil.copytree') as mock_copy:

            res = self.client.post(self.url, {'type': 'access', 'src': src, 'dst': dst, 'dip': str(ip.pk)})
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            mock_copy.assert_called_once_with(full_src, full_dst)

    def test_overwrite_dir_to_dip(self):
        self.url = reverse('workarea-files-add-to-dip')

        dstdir = 'dst'
        src = 'src'
        dst = 'dst'

        full_src = os.path.join('access', self.user.username, src)
        full_dst = os.path.join(dstdir, dst)

        ip = InformationPackage.objects.create(
            object_path=dstdir,
            responsible=self.user,
            package_type=InformationPackage.DIP
        )
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)

        exists = os.path.exists
        copytree_side_effects = [OSError(errno.EEXIST, "error"), mock.DEFAULT]
        with mock.patch('ESSArch_Core.ip.views.os.path.exists', side_effect=lambda x: x == full_src or exists(x)), \
                mock.patch('ESSArch_Core.ip.views.shutil.copytree', side_effect=copytree_side_effects) as mock_copy, \
                mock.patch('ESSArch_Core.ip.views.shutil.rmtree') as mock_rmtree:

            res = self.client.post(self.url, {'type': 'access', 'src': src, 'dst': dst, 'dip': str(ip.pk)})
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            mock_rmtree.assert_called_once_with(full_dst)

            copy_calls = [mock.call(full_src, full_dst),
                          mock.call(full_src, full_dst)]
            mock_copy.assert_has_calls(copy_calls)


class InformationPackageViewSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Path.objects.create(entity='ingest_workarea', value='')
        Path.objects.create(entity='access_workarea', value='')
        Path.objects.create(entity='disseminations', value='')
        Path.objects.create(entity="temp", value="temp")

        cls.org_group_type = GroupType.objects.create(label='organization')

    def setUp(self):
        self.user = User.objects.create(username="admin", password='admin')
        self.member = self.user.essauth_member
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
        self.assertEqual(len(res.data), 1)

        res = self.client.get(self.url, data={'view_type': 'aic', 'active': True})
        self.assertEqual(len(res.data), 0)

    def test_aic_view_type_with_ordering_and_filter(self):
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip14 = InformationPackage.objects.create(
            package_type=InformationPackage.AIP,
            aic=aic, generation=4, state='foo',
        )
        aip12 = InformationPackage.objects.create(
            package_type=InformationPackage.AIP,
            aic=aic, generation=2, state='foo',
        )
        aip13 = InformationPackage.objects.create(
            package_type=InformationPackage.AIP,
            aic=aic, generation=3, state='foo',
        )
        aip11 = InformationPackage.objects.create(
            package_type=InformationPackage.AIP,
            aic=aic, generation=1, state='foo',
        )
        aic2 = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip2 = InformationPackage.objects.create(
            package_type=InformationPackage.AIP,
            aic=aic2, generation=0, state='foo',
        )
        aic3 = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        aip3 = InformationPackage.objects.create(
            package_type=InformationPackage.AIP,
            aic=aic3, generation=0, state='bar',
        )

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
        start_date = make_aware(datetime(2000, 1, 1))
        aip = InformationPackage.objects.create(aic=aic, generation=0, state='foo', start_date=start_date)

        aic2 = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        start_date = make_aware(datetime(2010, 1, 1))
        aip2 = InformationPackage.objects.create(aic=aic2, generation=0, state='foo', start_date=start_date)

        aic3 = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        start_date = make_aware(datetime(2020, 1, 1))
        aip3 = InformationPackage.objects.create(aic=aic3, generation=0, state='bar', start_date=start_date)

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, aip, custom_permissions=perms)
        self.member.assign_object(self.group, aip2, custom_permissions=perms)
        self.member.assign_object(self.group, aip3, custom_permissions=perms)

        res = self.client.get(self.url, data={'view_type': 'ip', 'ordering': 'start_date', 'state': 'foo'})
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]['id'], str(aip.pk))
        self.assertEqual(res.data[1]['id'], str(aip2.pk))

        res = self.client.get(self.url, data={'view_type': 'ip', 'ordering': '-start_date', 'state': 'foo'})
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

        res = self.client.get(self.url, data={'view_type': 'aic', 'active': True})
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

        res = self.client.get(self.url, data={
            'view_type': 'aic', 'archived': False, 'active': True
        })
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

        res = self.client.get(self.url, data={
            'view_type': 'aic', 'archived': False, 'ordering': 'label',
            'active': True,
        })
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

        res = self.client.get(self.url, data={'view_type': 'aic', 'active': True})
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

        res = self.client.get(self.url, data={
            'view_type': 'ip', 'archived': True, 'active': True,
        })
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
        start_date = make_aware(datetime(2000, 1, 1))
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC, start_date=start_date)
        aip = InformationPackage.objects.create(generation=0, aic=aic, package_type=InformationPackage.AIP)
        aip2 = InformationPackage.objects.create(generation=1, aic=aic, package_type=InformationPackage.AIP)

        start_date = make_aware(datetime(2010, 1, 1))
        aic2 = InformationPackage.objects.create(package_type=InformationPackage.AIC, start_date=start_date)
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

        res = self.client.get(self.url, data={
            'view_type': 'aic', 'ordering': 'start_date', 'active': True,
        })
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]['id'], str(aic.pk))

        self.assertTrue(res.data[0]['information_packages'][0]['first_generation'])
        self.assertFalse(res.data[0]['information_packages'][0]['last_generation'])
        self.assertFalse(res.data[0]['information_packages'][1]['first_generation'])
        self.assertTrue(res.data[0]['information_packages'][1]['last_generation'])

        self.assertEqual(len(res.data[1]['information_packages']), 2)
        self.assertTrue(res.data[1]['information_packages'][0]['first_generation'])
        self.assertFalse(res.data[1]['information_packages'][0]['last_generation'])
        self.assertFalse(res.data[1]['information_packages'][1]['first_generation'])
        self.assertFalse(res.data[1]['information_packages'][1]['last_generation'])

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

    @mock.patch('ESSArch_Core.ip.views.ProcessTask.run')
    def test_delete_ip(self, mock_task):
        cache = StorageMethod.objects.create()
        ingest = Path.objects.create(entity='ingest', value='ingest')
        policy = StoragePolicy.objects.create(cache_storage=cache, ingest_path=ingest)

        sa = SubmissionAgreement.objects.create(policy=policy)
        ip = InformationPackage.objects.create(object_path='foo', submission_agreement=sa)
        url = reverse('informationpackage-detail', args=(str(ip.pk),))

        # no permission
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # view permission
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # delete permission
        perms = {'group': ['view_informationpackage', 'delete_informationpackage']}
        self.member.assign_object(self.group, ip, custom_permissions=perms)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_202_ACCEPTED)

        mock_task.assert_called_once()

    @mock.patch('ESSArch_Core.ip.views.ProcessTask.run')
    def test_delete_archived_ip(self, mock_task):
        ip = InformationPackage.objects.create(object_path='foo', responsible=self.user, archived=True)
        url = reverse('informationpackage-detail', args=(str(ip.pk),))
        res = self.client.delete(url)

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
        self.assertEqual(res.status_code, status.HTTP_202_ACCEPTED)

        mock_task.assert_called_once()

    @mock.patch('ESSArch_Core.ip.views.ProcessStep.run', side_effect=lambda *args, **kwargs: None)
    def test_preserve_aip(self, mock_step):
        Path.objects.create(entity='ingest_reception', value='ingest_reception')
        cache = StorageMethod.objects.create()
        ingest = Path.objects.create(entity='ingest', value='ingest')
        policy = StoragePolicy.objects.create(cache_storage=cache, ingest_path=ingest)
        aic = InformationPackage.objects.create(package_type=InformationPackage.AIC)
        sa = SubmissionAgreement.objects.create(policy=policy)
        self.ip = InformationPackage.objects.create(
            package_type=InformationPackage.AIP, aic=aic, submission_agreement=sa,
        )
        self.url = reverse('informationpackage-detail', args=(self.ip.pk,))
        self.url = self.url + 'preserve/'

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, self.ip, custom_permissions=perms)

        self.client.post(self.url)
        mock_step.assert_called_once()

        self.assertTrue(ProcessStep.objects.filter(information_package=self.ip).exists())

    @mock.patch('ESSArch_Core.ip.views.ProcessStep.run', side_effect=lambda *args, **kwargs: None)
    def test_preserve_dip(self, mock_step):
        Path.objects.create(entity='ingest_reception', value='ingest_reception')
        cache = StorageMethod.objects.create()
        ingest = Path.objects.create(entity='ingest', value='ingest')
        policy = StoragePolicy.objects.create(cache_storage=cache, ingest_path=ingest)
        sa = SubmissionAgreement.objects.create(policy=policy)
        self.ip = InformationPackage.objects.create(package_type=InformationPackage.DIP, submission_agreement=sa)
        self.url = reverse('informationpackage-preserve', args=(self.ip.pk,))

        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, self.ip, custom_permissions=perms)

        self.client.post(self.url)
        mock_step.assert_called_once()

        self.assertTrue(ProcessStep.objects.filter(information_package=self.ip).exists())

    def test_change_organization(self):
        self.ip = InformationPackage.objects.create(package_type=InformationPackage.DIP)
        self.url = reverse('informationpackage-change-organization', args=(self.ip.pk,))

        with self.subTest('without data'):
            res = self.client.post(self.url)
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        grp = Group.objects.create()
        with self.subTest('non-organization group'):
            res = self.client.post(self.url, data={'organization': grp.pk})
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        grp.group_type = self.org_group_type
        grp.save()
        with self.subTest('organization group without user'):
            res = self.client.post(self.url, data={'organization': grp.pk})
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        grp.add_member(self.member)
        with self.subTest('organization group with user'):
            res = self.client.post(self.url, data={'organization': grp.pk})
            self.assertEqual(res.status_code, status.HTTP_200_OK)

    @mock.patch('ESSArch_Core.ip.serializers.fill_specification_data', return_value={'foo': 'bar'})
    def test_get_ip_with_submission_agreement(self, mock_data):
        policy = StoragePolicy.objects.create(
            cache_storage=StorageMethod.objects.create(),
            ingest_path=Path.objects.create(),
        )
        sa = SubmissionAgreement.objects.create(
            policy=policy,
            template=[
                {
                    'key': 'foo',
                }
            ]
        )
        ip = InformationPackage.objects.create()

        sa_ip_data = SubmissionAgreementIPData.objects.create(
            user=self.user,
            submission_agreement=sa,
            information_package=ip,
        )
        ip.submission_agreement = sa
        ip.submission_agreement_data = sa_ip_data

        ip.save()

        self.client.get(self.url)


class InformationPackageReceptionViewSetTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cache = StorageMethod.objects.create()

        org_group_type = GroupType.objects.create(label='organization')
        cls.group = Group.objects.create(name='organization', group_type=org_group_type)
        cls.receive_perm = Permission.objects.get(content_type__app_label='ip', codename='receive')

    def add_user_to_group(self):
        self.group.add_member(self.user.essauth_member)

    def setUp(self):
        self.user = User.objects.create()
        self.client.force_authenticate(user=self.user)

        self.reception = tempfile.mkdtemp()
        temp = tempfile.mkdtemp()
        ingest_unidentified = tempfile.mkdtemp()
        ingest = tempfile.mkdtemp()

        self.addCleanup(shutil.rmtree, self.reception)
        self.addCleanup(shutil.rmtree, temp)
        self.addCleanup(shutil.rmtree, ingest_unidentified)
        self.addCleanup(shutil.rmtree, ingest)

        Path.objects.create(entity="temp", value=temp)
        Path.objects.create(entity='ingest_reception', value=self.reception)
        Path.objects.create(entity='ingest_unidentified', value=ingest_unidentified)
        ingest = Path.objects.create(entity='ingest', value=ingest)

        policy = StoragePolicy.objects.create(cache_storage=self.cache, ingest_path=ingest, receive_extract_sip=True)
        self.sa = SubmissionAgreement.objects.create(
            policy=policy,
            profile_aic_description=Profile.objects.create(profile_type='aic_description'),
            profile_aip=Profile.objects.create(
                profile_type='aip',
                structure=[
                    {
                        'type': 'file',
                        'name': 'mets.xml',
                        'use': 'mets_file',
                    },
                    {
                        'type': 'folder',
                        'name': 'content',
                        'use': 'content',
                        'children': [
                            {
                                'type': 'folder',
                                'name': '{{INNER_IP_OBJID}}',
                                'use': 'sip',
                            },
                        ]
                    },
                    {
                        'type': 'folder',
                        'name': 'metadata',
                        'use': 'metadata',
                        'children': [
                            {
                                'type': 'file',
                                'use': 'xsd_files',
                                'name': 'xsd_files'
                            },
                            {
                                'type': 'file',
                                'name': 'premis.xml',
                                'use': 'preservation_description_file',
                            },
                        ]
                    },
                ],
            ),
            profile_aip_description=Profile.objects.create(profile_type='aip_description'),
            profile_dip=Profile.objects.create(profile_type='dip'),
        )

    def get_package_path(self, objid):
        return os.path.join(self.reception, '{}.tar'.format(objid))

    def create_ip_package(self, objid):
        path = self.get_package_path(objid)
        with tarfile.open(path, 'w') as tar:
            tar.add(__file__, arcname='content/test.txt')
        return path

    def get_xml_path(self, objid):
        return os.path.join(self.reception, '{}.xml'.format(objid))

    def create_ip_xml(self, objid, package, sa):
        path = self.get_xml_path(objid)
        open(path, 'w').close()

        spec = {
            "-name": "mets",
            "-namespace": "mets",
            "-nsmap": {
                "mets": "http://www.loc.gov/METS/",
                "xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "xlink": "http://www.w3.org/1999/xlink"
            },
            "-attr": [
                {
                    "-name": "schemaLocation",
                    "-namespace": "xsi",
                    "#content": [
                        {
                            "text": "http://www.loc.gov/METS/ "
                            "http://xml.essarch.org/METS/version10/SubmitDescription.xsd"
                        }
                    ]
                },
                {
                    "-name": "ID",
                    "#content": "ID{% uuid4 %}"
                },
                {
                    "-name": "OBJID",
                    "#content": "UUID:{{OBJID}}"
                },
                {
                    "-name": "TYPE",
                    "#content": "SIP"
                },
                {
                    "-name": "PROFILE",
                    "#content": "http://example.com"
                }
            ],
            "-children": [
                {
                    "-name": "metsHdr",
                    "-namespace": "mets",
                    "-attr": [
                        {
                            "-name": "CREATEDATE",
                            "#content": "{% now 'c' %}"
                        }
                    ],
                    "-children": [
                        {
                            "-name": "agent",
                            "-namespace": "mets",
                            "-attr": [
                                {
                                    "-name": "ROLE",
                                    "#content": "CREATOR"
                                },
                                {
                                    "-name": "TYPE",
                                    "#content": "ORGANIZATION"
                                }
                            ],
                            "-children": [
                                {
                                    "-name": "name",
                                    "-namespace": "mets",
                                    "#content": "creator"
                                }
                            ]
                        },
                        {
                            "-name": "agent",
                            "-namespace": "mets",
                            "-attr": [
                                {
                                    "-name": "ROLE",
                                    "#content": "OTHER"
                                },
                                {
                                    "-name": "OTHERROLE",
                                    "#content": "SUBMITTER"
                                },
                                {
                                    "-name": "TYPE",
                                    "#content": "ORGANIZATION"
                                }
                            ],
                            "-children": [
                                {
                                    "-name": "name",
                                    "-namespace": "mets",
                                    "#content": "submitter_organization"
                                }
                            ]
                        },
                        {
                            "-name": "agent",
                            "-namespace": "mets",
                            "-attr": [
                                {
                                    "-name": "ROLE",
                                    "#content": "OTHER"
                                },
                                {
                                    "-name": "OTHERROLE",
                                    "#content": "SUBMITTER"
                                },
                                {
                                    "-name": "TYPE",
                                    "#content": "INDIVIDUAL"
                                }
                            ],
                            "-children": [
                                {
                                    "-name": "name",
                                    "-namespace": "mets",
                                    "#content": "submitter_individual"
                                }
                            ]
                        },
                        {
                            "-name": "altRecordID",
                            "-namespace": "mets",
                            "-attr": [
                                {
                                    "-name": "TYPE",
                                    "#content": "SUBMISSIONAGREEMENT"
                                }
                            ],
                            "#content": str(sa.pk)
                        },
                        {
                            "-name": "altRecordID",
                            "-namespace": "mets",
                            "-attr": [
                                {
                                    "-name": "TYPE",
                                    "#content": "STARTDATE"
                                }
                            ],
                            "#content": "2020-01-01 00:00:00+00:00"
                        },
                        {
                            "-name": "altRecordID",
                            "-namespace": "mets",
                            "-attr": [
                                {
                                    "-name": "TYPE",
                                    "#content": "ENDDATE"
                                }
                            ],
                            "#content": "2020-12-31 00:00:00+00:00"
                        },
                    ]
                },
                {
                    "-name": "fileSec",
                    "-namespace": "mets",
                    "-attr": [
                        {
                            "-name": "ID",
                            "#content": "ID{{UUID}}"
                        }
                    ],
                    "-children": [
                        {
                            "-name": "fileGrp",
                            "-namespace": "mets",
                            "-children": [
                                {
                                    "-name": "file",
                                    "-namespace": "mets",
                                    "-containsFiles": True,
                                    "-filters": {"href": r".+\.tar$"},
                                    "-attr": [
                                        {
                                            "-name": "ID",
                                            "#content": "ID{{FID}}"
                                        },
                                        {
                                            "-name": "MIMETYPE",
                                            "#content": "{{FMimetype}}"
                                        },
                                        {
                                            "-name": "SIZE",
                                            "#content": "{{FSize}}"
                                        },
                                        {
                                            "-name": "USE",
                                            "#content": "{{FUse}}"
                                        },
                                        {
                                            "-name": "CREATED",
                                            "#content": "{{FCreated}}"
                                        },
                                        {
                                            "-name": "CHECKSUM",
                                            "#content": "{{FChecksum}}"
                                        },
                                        {
                                            "-name": "CHECKSUMTYPE",
                                            "#content": "{{FChecksumType}}"
                                        }
                                    ],
                                    "-children": [
                                        {
                                            "-name": "FLocat",
                                            "-namespace": "mets",
                                            "-attr": [
                                                {
                                                    "-name": "LOCTYPE",
                                                    "#content": "URL"
                                                },
                                                {
                                                    "-name": "href",
                                                    "-namespace": "xlink",
                                                    "#content": "file:///{{href}}"
                                                },
                                                {
                                                    "-name": "type",
                                                    "-namespace": "xlink",
                                                    "#content": "simple"
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {
                    "-name": "structMap",
                    "-namespace": "mets",
                    "-children": [
                        {
                            "-name": "div",
                            "-namespace": "mets",
                            "-attr": [
                                {
                                    "-name": "LABEL",
                                    "#content": "Package"
                                }
                            ],
                            "-children": [
                                {
                                    "-name": "div",
                                    "-namespace": "mets",
                                    "-attr": [
                                        {
                                            "-name": "LABEL",
                                            "#content": "Datafiles"
                                        }
                                    ],
                                    "-children": [
                                        {
                                            "-name": "fptr",
                                            "-namespace": "mets",
                                            "-containsFiles": True,
                                            "-attr": [
                                                {
                                                    "-name": "FILEID",
                                                    "#content": "ID{{FID}}"
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        XMLGenerator().generate(filesToCreate={path: {'spec': spec}}, folderToParse=package)
        return path

    def test_receive_without_permission(self):
        url = reverse('ip-reception-receive', args=('foo',))
        res = self.client.post(url, data={})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_receive_existing_non_sip(self):
        self.user.user_permissions.add(self.receive_perm)

        package_types = [
            InformationPackage.AIC,
            InformationPackage.AIP,
            InformationPackage.AIU,
            InformationPackage.DIP,
        ]
        for package_type in package_types:
            with self.subTest(package_type):
                ip = InformationPackage.objects.create(
                    object_identifier_value='existing_{}'.format(package_type),
                    package_type=package_type,
                )
                url = reverse('ip-reception-receive', args=(ip.object_identifier_value,))
                res = self.client.post(url)
                self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    def test_receive_invalid_xml(self):
        self.user.user_permissions.add(self.receive_perm)

        xml_path = self.get_xml_path("invalid-xml")
        with open(xml_path, 'w') as f:
            f.write('invalid')

        url = reverse('ip-reception-receive', args=('invalid-xml',))
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_receive_missing_xml(self):
        self.user.user_permissions.add(self.receive_perm)

        url = reverse('ip-reception-receive', args=('does-not-exist',))
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_receive_missing_package(self):
        self.user.user_permissions.add(self.receive_perm)

        objid = 'foo'
        ip_package = self.create_ip_package(objid)
        self.create_ip_xml(objid, ip_package, self.sa)
        os.remove(ip_package)

        url = reverse('ip-reception-receive', args=(objid,))
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_receive_missing_profiles(self):
        self.user.user_permissions.add(self.receive_perm)
        self.add_user_to_group()

        objid = 'foo'
        ip_package = self.create_ip_package(objid)
        self.create_ip_xml(objid, ip_package, self.sa)

        profile_types = [
            'dip',
            'aip_description',
            'aip',
            'aic_description',
        ]
        for ptype in profile_types:
            with self.subTest(ptype):
                setattr(self.sa, 'profile_{}'.format(ptype), None)
                self.sa.save()

                url = reverse('ip-reception-receive', args=(objid,))
                res = self.client.post(url, data={})
                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_receive_without_organization(self):
        self.user.user_permissions.add(self.receive_perm)

        objid = 'foo'
        ip_package = self.create_ip_package(objid)
        self.create_ip_xml(objid, ip_package, self.sa)

        url = reverse('ip-reception-receive', args=(objid,))
        res = self.client.post(url, data={})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @TaskRunner()
    def test_receive_existing_sip(self):
        self.user.user_permissions.add(self.receive_perm)
        self.add_user_to_group()

        objid = 'foo'
        ip_package = self.create_ip_package(objid)
        self.create_ip_xml(objid, ip_package, self.sa)

        ip = InformationPackage.objects.create(
            object_identifier_value=objid,
            package_type=InformationPackage.SIP,
            object_path=ip_package,
            submission_agreement=self.sa,
        )
        self.sa.lock_to_information_package(ip, self.user)

        url = reverse('ip-reception-receive', args=(objid,))
        res = self.client.post(url, data={})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        aip = InformationPackage.objects.get(object_identifier_value=objid, package_type=InformationPackage.AIP)
        with open(os.path.join(aip.object_path, 'content/foo/content/test.txt')) as f, open(__file__) as expected:
            self.assertEqual(f.read(), expected.read())

    def test_receive_ip_missing_sa(self):
        self.user.user_permissions.add(self.receive_perm)
        self.add_user_to_group()

        objid = 'foo'
        ip_package = self.create_ip_package(objid)
        xml = self.create_ip_xml(objid, ip_package, self.sa)

        tree = etree.parse(xml)
        for sa_el in tree.xpath("//*[local-name()='altRecordID'][@TYPE='SUBMISSIONAGREEMENT']"):
            sa_el.getparent().remove(sa_el)
        with open(xml, 'wb') as f:
            tree.write(f, encoding="utf-8", xml_declaration=True)

        url = reverse('ip-reception-receive', args=(objid,))
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_receive_ip_non_matching_parsed_and_provided_sa(self):
        self.user.user_permissions.add(self.receive_perm)
        self.add_user_to_group()

        objid = 'foo'
        ip_package = self.create_ip_package(objid)
        self.create_ip_xml(objid, ip_package, self.sa)

        url = reverse('ip-reception-receive', args=(objid,))
        res = self.client.post(url, data={'submission_agreement': "invalid-sa"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_receive_ip_matching_parsed_and_provided_sa(self):
        self.user.user_permissions.add(self.receive_perm)
        self.add_user_to_group()

        objid = 'foo'
        ip_package = self.create_ip_package(objid)
        self.create_ip_xml(objid, ip_package, self.sa)

        url = reverse('ip-reception-receive', args=(objid,))
        res = self.client.post(url, data={'submission_agreement': str(self.sa.pk)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    @TaskRunner()
    def test_receive_ip(self):
        self.user.user_permissions.add(self.receive_perm)
        self.add_user_to_group()

        objid = 'foo'
        ip_package = self.create_ip_package(objid)
        self.create_ip_xml(objid, ip_package, self.sa)

        url = reverse('ip-reception-receive', args=(objid,))
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        aip = InformationPackage.objects.get(object_identifier_value=objid, package_type=InformationPackage.AIP)
        with open(os.path.join(aip.object_path, 'content/foo/content/test.txt')) as f, open(__file__) as expected:
            self.assertEqual(f.read(), expected.read())


class InformationPackageChangeSubmissionAgreementTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.policy = StoragePolicy.objects.create(
            cache_storage=StorageMethod.objects.create(),
            ingest_path=Path.objects.create(),
        )
        cls.sa1 = SubmissionAgreement.objects.create(policy=cls.policy)
        cls.sa2 = SubmissionAgreement.objects.create(policy=cls.policy)

        Path.objects.create(entity='temp', value='')

    def setUp(self):
        self.user = User.objects.create(username="admin", password='admin')
        permissions = Permission.objects.filter(codename__in=[
            'change_sa', 'change_submissionagreementipdata',
        ])
        self.user.user_permissions.add(*permissions)
        self.member = self.user.essauth_member

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.ip = InformationPackage.objects.create(submission_agreement=self.sa1)
        self.url = reverse('informationpackage-detail', args=(str(self.ip.pk),))

    def test_change_submission_agreement(self):
        res = self.client.patch(self.url, data={'submission_agreement': str(self.sa2.pk)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(res.data['submission_agreement_data'])
        self.ip.refresh_from_db()
        self.assertEqual(self.ip.submission_agreement, self.sa2)

    def test_change_submission_agreement_data(self):
        new_data = SubmissionAgreementIPData.objects.create(
            submission_agreement=self.sa1,
            information_package=self.ip,
            data={'hello': 'world'},
            user=self.user,
        )
        res = self.client.patch(self.url, data={'submission_agreement_data': str(new_data.pk)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.ip.refresh_from_db()
        self.assertEqual(self.ip.submission_agreement_data, new_data)

    def test_change_submission_agreement_and_data(self):
        new_sa = SubmissionAgreement.objects.create(policy=self.policy)
        new_data = SubmissionAgreementIPData.objects.create(
            submission_agreement=new_sa,
            information_package=self.ip,
            data={'hello': 'world'},
            user=self.user,
        )
        res = self.client.patch(self.url, data={
            'submission_agreement': str(self.sa2.pk),
            'submission_agreement_data': str(new_data.pk)
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.ip.refresh_from_db()
        self.assertIsNone(self.ip.submission_agreement_data)

        res = self.client.patch(self.url, data={
            'submission_agreement': str(new_sa.pk),
            'submission_agreement_data': str(new_data.pk)
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.ip.refresh_from_db()
        self.assertEqual(self.ip.submission_agreement_data, new_data)

    def test_set_data_when_changing_submission_agreement(self):
        sa1_data = SubmissionAgreementIPData.objects.create(
            submission_agreement=self.sa1,
            information_package=self.ip,
            data={'hello': 'world'},
            user=self.user,
        )
        self.ip.submission_agreement_data = sa1_data
        self.ip.save()

        res = self.client.patch(self.url, data={
            'submission_agreement': str(self.sa2.pk),
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.ip.refresh_from_db()
        self.assertIsNone(self.ip.submission_agreement_data)

        with self.subTest('change to SA with existing data'):
            res = self.client.patch(self.url, data={
                'submission_agreement': str(self.sa1.pk),
            })
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.ip.refresh_from_db()
            self.assertEqual(self.ip.submission_agreement_data, sa1_data)

    def test_change_locked_submission_agreement(self):
        self.ip.submission_agreement_locked = True
        self.ip.save()

        res = self.client.patch(self.url, data={'submission_agreement': str(self.sa2.pk)})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.ip.refresh_from_db()
        self.assertEqual(self.ip.submission_agreement, self.sa1)

    def test_change_locked_submission_agreement_data(self):
        self.ip.submission_agreement_locked = True
        self.ip.save()

        new_data = SubmissionAgreementIPData.objects.create(
            submission_agreement=self.sa1,
            information_package=self.ip,
            data={'hello': 'world'},
            user=self.user,
        )
        res = self.client.patch(self.url, data={'submission_agreement_data': str(new_data.pk)})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.ip.refresh_from_db()
        self.assertIsNone(self.ip.submission_agreement_data)

    def test_change_invalid_submission_agreement_data(self):
        with self.subTest('wrong sa'):
            new_data = SubmissionAgreementIPData.objects.create(
                submission_agreement=self.sa2,
                information_package=self.ip,
                data={'hello': 'world'},
                user=self.user,
            )
            res = self.client.patch(self.url, data={'submission_agreement_data': str(new_data.pk)})

            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.ip.refresh_from_db()
            self.assertIsNone(self.ip.submission_agreement_data)

        with self.subTest('wrong ip'):
            new_ip = InformationPackage.objects.create()
            new_data = SubmissionAgreementIPData.objects.create(
                submission_agreement=self.sa1,
                information_package=new_ip,
                data={'hello': 'world'},
                user=self.user,
            )
            res = self.client.patch(self.url, data={'submission_agreement_data': str(new_data.pk)})

            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.ip.refresh_from_db()
            self.assertIsNone(self.ip.submission_agreement_data)


class OrderViewSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.order_type = OrderType.objects.create(name="foo")

    def setUp(self):
        self.user = User.objects.create(username="admin")

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        orders_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, orders_dir)
        self.orders_path = Path.objects.create(entity="orders", value=orders_dir)

    def test_list_empty(self):
        url = reverse('order-list')
        res = self.client.get(url)

        self.assertEqual(res.data, [])

    def test_list_only_owned(self):
        other_user = User.objects.create(username="user")
        order = Order.objects.create(responsible=self.user, type=self.order_type)
        Order.objects.create(responsible=other_user, type=self.order_type)

        url = reverse('order-list')
        res = self.client.get(url)

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], str(order.pk))

    def test_list_all_if_superuser(self):
        other_user = User.objects.create(username="user")
        Order.objects.create(responsible=self.user, type=self.order_type)
        Order.objects.create(responsible=other_user, type=self.order_type)

        self.user.is_superuser = True
        self.user.save()

        url = reverse('order-list')
        res = self.client.get(url)

        self.assertEqual(len(res.data), 2)

    def test_detail_owned(self):
        order = Order.objects.create(responsible=self.user, type=self.order_type)

        url = reverse('order-detail', args=[order.pk])
        res = self.client.get(url)

        self.assertEqual(res.data['id'], str(order.pk))

    def test_detail_non_existing(self):
        url = reverse('order-detail', args=[uuid.uuid4()])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_deny_detail_other(self):
        other_user = User.objects.create(username="user")
        order = Order.objects.create(responsible=other_user, type=self.order_type)

        url = reverse('order-detail', args=[order.pk])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_other_super_user(self):
        other_user = User.objects.create(username="user")
        order = Order.objects.create(responsible=other_user, type=self.order_type)

        self.user.is_superuser = True
        self.user.save()

        url = reverse('order-detail', args=[order.pk])
        res = self.client.get(url)

        self.assertEqual(res.data['id'], str(order.pk))

    def test_create_without_ip(self):
        url = reverse('order-list')
        res = self.client.post(url, {'label': 'foo', 'type': self.order_type.pk})

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['label'], 'foo')
        self.assertTrue(Order.objects.filter(label='foo', responsible=self.user).exists())

    def test_create_with_dip(self):
        url = reverse('order-list')
        ip = InformationPackage.objects.create(package_type=InformationPackage.DIP)
        ip_url = reverse('informationpackage-detail', args=[ip.pk])
        res = self.client.post(url, {'label': 'foo', 'information_packages': [ip_url], 'type': self.order_type.pk})

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.first().information_packages.first(), ip)

    def test_create_with_ip_other_than_dip(self):
        url = reverse('order-list')
        ip = InformationPackage.objects.create(package_type=InformationPackage.SIP)
        ip_url = reverse('informationpackage-detail', args=[ip.pk])
        res = self.client.post(url, {'label': 'foo', 'information_packages': [ip_url]})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_download(self):
        order = Order.objects.create(label='order1', responsible=self.user, type=self.order_type)
        url = reverse('order-download', args=[order.pk])

        os.makedirs(order.path)

        with open(os.path.join(order.path, 'foo.txt'), 'w') as f:
            f.write('test foo')

        with open(os.path.join(order.path, 'bar.pdf'), 'w') as f:
            f.write('test bar')

        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res['Content-Type'], 'application/zip; charset=utf-8')
        self.assertEqual(res['Content-Disposition'], 'attachment; filename="order1.zip"')

        data = io.BytesIO(res.getvalue())
        with zipfile.ZipFile(data) as zip_file:
            self.assertEqual(zip_file.read('order1/foo.txt'), b'test foo')
            self.assertEqual(zip_file.read('order1/bar.pdf'), b'test bar')


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class IdentifyIP(TestCase):
    @classmethod
    def setUpTestData(cls):
        EventType.objects.create(eventType=50600, category=EventType.CATEGORY_INFORMATION_PACKAGE)

    def setUp(self):
        self.bd = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.bd, "datafiles")

        try:
            os.mkdir(self.datadir)
        except BaseException:
            pass

        self.addCleanup(shutil.rmtree, self.datadir)

        mimetypes_file = Path.objects.create(
            entity="mimetypes_definitionfile",
            value=os.path.join(self.datadir, "mime.types"),
        ).value
        with open(mimetypes_file, 'w') as f:
            f.write('application/x-tar tar')

        self.path = Path.objects.create(entity="ingest_unidentified", value=self.datadir).value
        Path.objects.create(entity="ingest_reception", value="ingest_reception")

        self.user = User.objects.create(username="admin")

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.reception_url = reverse('ip-reception-list')
        self.identify_url = '%sidentify-ip/' % self.reception_url

        self.objid = 'unidentified_ip'
        fpath = os.path.join(self.path, '%s.tar' % self.objid)
        open(fpath, 'a').close()

    def test_identify_ip(self):
        data = {
            'filename': '%s.tar' % self.objid,
            'specification_data': {
                'ObjectIdentifierValue': 'my obj',
                'LABEL': 'my label',
                'profile': 'my profile',
                'RECORDSTATUS': 'my recordstatus',
            },
        }

        res = self.client.post(self.identify_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        xmlfile = os.path.join(self.path, '%s.xml' % self.objid)
        self.assertTrue(os.path.isfile(xmlfile))

        doc = etree.parse(xmlfile)
        root = doc.getroot()

        self.assertEqual(root.get('OBJID').split(':')[1], data['specification_data']['ObjectIdentifierValue'])
        self.assertEqual(root.get('LABEL'), data['specification_data']['LABEL'])

    def test_identify_ip_no_objid(self):
        data = {
            'filename': '%s.tar' % self.objid,
            'specification_data': {
                'LABEL': 'my label',
                'profile': 'my profile',
                'RECORDSTATUS': 'my recordstatus',
            },
        }

        res = self.client.post(self.identify_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        xmlfile = os.path.join(self.path, '%s.xml' % self.objid)
        self.assertTrue(os.path.isfile(xmlfile))

        doc = etree.parse(xmlfile)
        root = doc.getroot()

        self.assertEqual(root.get('OBJID').split(':')[1], self.objid)
        self.assertEqual(root.get('LABEL'), data['specification_data']['LABEL'])

    def test_identify_ip_no_label(self):
        data = {
            'filename': '%s.tar' % self.objid,
            'specification_data': {
                'ObjectIdentifierValue': 'my obj',
                'profile': 'my profile',
                'RECORDSTATUS': 'my recordstatus',
            },
        }

        res = self.client.post(self.identify_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        xmlfile = os.path.join(self.path, '%s.xml' % self.objid)
        self.assertTrue(os.path.isfile(xmlfile))

        doc = etree.parse(xmlfile)
        root = doc.getroot()

        self.assertEqual(root.get('OBJID').split(':')[1], data['specification_data']['ObjectIdentifierValue'])
        self.assertEqual(root.get('LABEL'), self.objid)


class CreateIPTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = os.path.dirname(os.path.realpath(__file__))
        cls.datadir = os.path.join(cls.root, 'datadir')
        Path.objects.create(entity='preingest', value=cls.datadir)
        Path.objects.create(entity='disseminations', value=cls.datadir)

        EventType.objects.create(eventType=10100, category=EventType.CATEGORY_INFORMATION_PACKAGE)
        EventType.objects.create(eventType=10200, category=EventType.CATEGORY_INFORMATION_PACKAGE)

        cls.url = reverse('informationpackage-list')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member
        self.client.force_authenticate(user=self.user)

        self.addCleanup(shutil.rmtree, self.datadir)

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def get_add_permission(self):
        return Permission.objects.get(codename='add_informationpackage')

    def add_to_organization(self):
        self.org_group_type = GroupType.objects.create(label='organization')
        self.org = Group.objects.create(name='organization', group_type=self.org_group_type)

        self.user_role = GroupMemberRole.objects.create(codename='user_role')

        membership = GroupMember.objects.create(member=self.member, group=self.org)
        membership.roles.add(self.user_role)

    def test_without_permission(self):
        data = {'label': 'my label', 'object_identifier_value': 'my objid'}

        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(InformationPackage.objects.exists())

    def test_without_organization(self):
        perm = self.get_add_permission()
        self.user.user_permissions.add(perm)

        data = {'label': 'my label', 'object_identifier_value': 'my objid'}
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(InformationPackage.objects.exists())

    def test_create_ip(self):
        self.add_to_organization()
        perm = self.get_add_permission()
        self.user_role.permissions.add(perm)

        data = {'package_type': InformationPackage.SIP, 'label': 'my label', 'object_identifier_value': 'my objid'}
        res = self.client.post(self.url, data)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            InformationPackage.objects.filter(
                responsible=self.user,
                label=data['label'],
                object_identifier_value=data['object_identifier_value'],
            ).exists()
        )

    def test_create_ip_without_objid(self):
        self.add_to_organization()
        perm = self.get_add_permission()
        self.user_role.permissions.add(perm)

        data = {'package_type': InformationPackage.SIP, 'label': 'my label'}

        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        ip = InformationPackage.objects.get()
        self.assertEqual(str(ip.pk), ip.object_identifier_value)

    def test_create_ip_without_label(self):
        self.add_to_organization()
        perm = self.get_add_permission()
        self.user_role.permissions.add(perm)

        data = {'package_type': InformationPackage.SIP, 'object_identifier_value': 'my objid'}
        res = self.client.post(self.url, data)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(InformationPackage.objects.exists())

    def test_create_ip_with_same_objid_as_existing(self):
        self.add_to_organization()
        perm = self.get_add_permission()
        self.user_role.permissions.add(perm)

        existing = InformationPackage.objects.create(object_identifier_value='objid')

        data = {'package_type': InformationPackage.SIP, 'label': 'my label', 'object_identifier_value': 'objid'}
        res = self.client.post(self.url, data)

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(InformationPackage.objects.count(), 1)
        self.assertEqual(InformationPackage.objects.first().pk, existing.pk)

    def test_create_ip_with_same_objid_as_existing_on_disk_but_not_db(self):
        self.add_to_organization()
        perm = self.get_add_permission()
        self.user_role.permissions.add(perm)

        os.mkdir(os.path.join(self.datadir, 'objid'))
        data = {'package_type': InformationPackage.SIP, 'label': 'my label', 'object_identifier_value': 'objid'}
        res = self.client.post(self.url, data)

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(InformationPackage.objects.exists())

    def test_create_ip_with_invalid_objid(self):
        self.add_to_organization()
        perm = self.get_add_permission()
        self.user_role.permissions.add(perm)

        invalid_characters = '\\/:*?"<>|'
        for c in invalid_characters:
            with self.subTest(c):
                data = {
                    'package_type': InformationPackage.SIP,
                    'label': 'my label',
                    'object_identifier_value': 'objid{}'.format(c)
                }
                res = self.client.post(self.url, data)

                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(
                    res.data['object_identifier_value'],
                    ['Invalid character: {}'.format(c)],
                )
                self.assertFalse(InformationPackage.objects.exists())

        with self.subTest(invalid_characters):
            data = {
                'package_type': InformationPackage.SIP,
                'label': 'my label',
                'object_identifier_value': 'objid{}'.format(invalid_characters)
            }
            res = self.client.post(self.url, data)
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                res.data['object_identifier_value'],
                ['Invalid character: {}'.format(invalid_characters[0])],
            )
            self.assertFalse(InformationPackage.objects.exists())

    def test_create_ip_with_same_label_as_existing(self):
        self.add_to_organization()
        perm = self.get_add_permission()
        self.user_role.permissions.add(perm)

        InformationPackage.objects.create(label='label')
        data = {'package_type': InformationPackage.SIP, 'label': 'label'}
        res = self.client.post(self.url, data)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InformationPackage.objects.filter(label='label').count(), 2)

    def test_create_dip_with_existing_object_identifier_value(self):
        self.add_to_organization()
        perm = self.get_add_permission()
        self.user_role.permissions.add(perm)

        InformationPackage.objects.create(object_identifier_value='bar')
        data = {'package_type': InformationPackage.DIP, 'label': 'foo', 'object_identifier_value': 'bar'}
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    def test_create_dip_with_non_existing_order(self):
        self.add_to_organization()
        perm = self.get_add_permission()
        self.user_role.permissions.add(perm)

        order_type = OrderType.objects.create(name='foo')
        orders = [str(Order.objects.create(responsible=self.user, type=order_type).pk), str(uuid.uuid4())]
        data = {'package_type': InformationPackage.DIP, 'label': 'foo', 'orders': orders}
        res = self.client.post(self.url, data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['orders'][1][0].code, 'does_not_exist')

    def test_create_dip_with_existing_order(self):
        self.add_to_organization()
        perm = self.get_add_permission()
        self.user_role.permissions.add(perm)

        order_type = OrderType.objects.create(name='foo')
        order = Order.objects.create(responsible=self.user, type=order_type)
        data = {'package_type': InformationPackage.DIP, 'label': 'foo', 'orders': [str(order.pk)]}
        res = self.client.post(self.url, data)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(order.information_packages.exists())


class PrepareIPTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        policy = StoragePolicy.objects.create(
            cache_storage=StorageMethod.objects.create(),
            ingest_path=Path.objects.create(),
        )
        cls.sa = SubmissionAgreement.objects.create(policy=policy)

        Path.objects.create(entity='temp')
        EventType.objects.create(eventType=10300, category=EventType.CATEGORY_INFORMATION_PACKAGE)

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member
        self.client.force_authenticate(user=self.user)

    def get_prepare_permission(self):
        return Permission.objects.get(codename='prepare_ip')

    def create_profile(self, profile_type):
        return Profile.objects.create(profile_type=profile_type)

    def test_without_permission(self):
        ip = InformationPackage.objects.create()
        url = reverse('informationpackage-prepare', args=(ip.pk,))

        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_state(self):
        perm = self.get_prepare_permission()
        self.user.user_permissions.add(perm)

        ip = InformationPackage.objects.create()
        url = reverse('informationpackage-prepare', args=(ip.pk,))

        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['detail'], 'IP must be in state "Preparing"')

    def test_unlocked_sa(self):
        perm = self.get_prepare_permission()
        self.user.user_permissions.add(perm)

        ip = InformationPackage.objects.create(state='Preparing', submission_agreement=self.sa)
        url = reverse('informationpackage-prepare', args=(ip.pk,))

        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['detail'], 'IP requires locked SA to be prepared')

    def test_missing_profiles(self):
        perm = self.get_prepare_permission()
        self.user.user_permissions.add(perm)

        ip = InformationPackage.objects.create(
            state='Preparing', submission_agreement=self.sa,
            submission_agreement_locked=True,
        )
        url = reverse('informationpackage-prepare', args=(ip.pk,))

        with self.subTest('SIP without SIP profile'):
            res = self.client.post(url)
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(res.data['detail'], 'Information package missing SIP profile')

        with self.subTest('SIP without submit description profile'):
            sip_profile = self.create_profile('sip')
            ProfileIP.objects.create(ip=ip, profile=sip_profile)
            self.sa.profile_sip = sip_profile
            self.sa.save()

            res = self.client.post(url)
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(res.data['detail'], 'Information package missing Submit Description profile')

        with self.subTest('SIP without transfer project profile'):
            submit_description_profile = self.create_profile('submit_description')
            ProfileIP.objects.create(ip=ip, profile=submit_description_profile)
            self.sa.profile_submit_description = submit_description_profile
            self.sa.save()

            res = self.client.post(url)
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(res.data['detail'], 'Information package missing Transfer Project profile')

        with self.subTest('DIP without DIP profile'):
            transfer_project_profile = self.create_profile('transfer_project')
            ProfileIP.objects.create(ip=ip, profile=transfer_project_profile)
            self.sa.profile_transfer_project = transfer_project_profile
            self.sa.save()

            ip.package_type = InformationPackage.DIP
            ip.save()
            res = self.client.post(url)
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(res.data['detail'], 'Information package missing DIP profile')

        with self.subTest('Valid DIP'):
            dip_profile = self.create_profile('dip')
            ProfileIP.objects.create(ip=ip, profile=dip_profile)
            self.sa.profile_dip = dip_profile
            self.sa.save()

            res = self.client.post(url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        with self.subTest('Valid SIP'):
            ip.package_type = InformationPackage.SIP
            ip.state = 'Preparing'
            ip.save()

            res = self.client.post(url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        ip.refresh_from_db()
        self.assertEqual(ip.state, 'Prepared')


class DownloadIPTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='user')
        cls.member = cls.user.essauth_member

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        f = tempfile.NamedTemporaryFile(suffix='.tar', delete=False)
        f.close()
        self.ip = InformationPackage.objects.create(object_path=f.name)
        self.addCleanup(os.remove, self.ip.object_path)

        self.url = reverse('informationpackage-download', args=(str(self.ip.pk),))

    def test_download(self):
        with self.subTest('invalid package type'):
            res = self.client.get(self.url)
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        self.ip.package_type = InformationPackage.DIP
        self.ip.save()

        with self.subTest('invalid state'):
            res = self.client.get(self.url)
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        self.ip.state = 'Created'
        self.ip.save()

        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res['Content-Type'], 'application/x-tar; charset=utf-8')
        self.assertEqual(
            res['Content-Disposition'],
            'attachment; filename="{}"'.format(os.path.basename(self.ip.object_path)),
        )


class test_submit_ip(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = os.path.dirname(os.path.realpath(__file__))
        cls.datadir = os.path.join(cls.root, 'datadir')

        Path.objects.create(entity='preingest', value=cls.datadir)
        Path.objects.create(entity='preingest_reception', value=cls.datadir)

    def setUp(self):
        self.user = User.objects.create(username="admin")

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        policy = StoragePolicy.objects.create(
            cache_storage=StorageMethod.objects.create(),
            ingest_path=Path.objects.create(),
        )

        self.sa = SubmissionAgreement.objects.create(policy=policy)
        self.ip = InformationPackage.objects.create(submission_agreement=self.sa)
        self.url = reverse('informationpackage-submit', args=(self.ip.pk,))

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def tearDown(self):
        try:
            shutil.rmtree(self.datadir)
        except BaseException:
            pass

    def test_not_responsible(self):
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_created(self):
        self.ip.responsible = self.user
        self.ip.save()
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_submit_description_profile(self):
        self.ip.responsible = self.user
        self.ip.state = 'Created'
        self.ip.save()
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('ESSArch_Core.ip.views.creation_date', return_value=0)
    @mock.patch('ESSArch_Core.ip.views.ProcessStep.run')
    def test_no_mail(self, mock_step, mock_time):
        self.ip.responsible = self.user
        self.ip.state = 'Created'
        self.ip.save()

        sd = Profile.objects.create(profile_type='submit_description')
        ProfileIP.objects.create(ip=self.ip, profile=sd)

        res = self.client.post(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertFalse(ProcessTask.objects.filter(name="ESSArch_Core.tasks.SendEmail").exists())
        mock_step.assert_called_once()

    def test_with_mail_without_subject(self):
        self.ip.responsible = self.user
        self.ip.state = 'Created'
        self.ip.save()

        tp = Profile.objects.create(
            profile_type='transfer_project',
        )
        tp_ip = ProfileIP.objects.create(ip=self.ip, profile=tp)
        tp_ip_data = ProfileIPData.objects.create(
            relation=tp_ip,
            data={'preservation_organization_receiver_email': 'foo'},
            user=self.user,
        )
        tp_ip.data = tp_ip_data
        tp_ip.save()

        res = self.client.post(self.url, {'body': 'foo'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_with_mail_without_body(self):
        self.ip.responsible = self.user
        self.ip.state = 'Created'
        self.ip.save()

        tp = Profile.objects.create(
            profile_type='transfer_project',
        )
        tp_ip = ProfileIP.objects.create(ip=self.ip, profile=tp)
        tp_ip_data = ProfileIPData.objects.create(
            relation=tp_ip,
            data={'preservation_organization_receiver_email': 'foo'},
            user=self.user,
        )
        tp_ip.data = tp_ip_data
        tp_ip.save()

        res = self.client.post(self.url, {'subject': 'foo'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('ESSArch_Core.ip.views.creation_date', return_value=0)
    @mock.patch('ESSArch_Core.ip.views.ProcessStep.run')
    def test_with_mail(self, mock_step, mock_time):
        self.ip.responsible = self.user
        self.ip.state = 'Created'
        self.ip.save()

        tp = Profile.objects.create(
            profile_type='transfer_project',
        )
        tp_ip = ProfileIP.objects.create(ip=self.ip, profile=tp)
        tp_ip_data = ProfileIPData.objects.create(
            relation=tp_ip,
            data={'preservation_organization_receiver_email': 'foo'},
            user=self.user,
        )
        tp_ip.data = tp_ip_data
        tp_ip.save()

        sd = Profile.objects.create(profile_type='submit_description')
        ProfileIP.objects.create(ip=self.ip, profile=sd)

        res = self.client.post(self.url, {'subject': 'foo', 'body': 'bar'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertTrue(ProcessTask.objects.filter(name="ESSArch_Core.tasks.SendEmail").exists())
        mock_step.assert_called_once()


class test_set_uploaded(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="admin")

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.ip = InformationPackage.objects.create(state='Uploading')
        self.url = reverse('informationpackage-set-uploaded', args=(self.ip.pk,))

    def test_set_uploaded_without_permission(self):
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.state, 'Uploading')

    @TaskRunner()
    def test_set_uploaded_with_permission(self):
        InformationPackage.objects.filter(pk=self.ip.pk).update(
            responsible=self.user
        )

        res = self.client.post(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.state, 'Uploaded')


class UploadTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('user')
        self.member = self.user.essauth_member
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        EventType.objects.create(eventType=50700, category=EventType.CATEGORY_INFORMATION_PACKAGE)

        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, 'datadir')
        self.src = os.path.join(self.datadir, 'src')
        self.dst = os.path.join(self.datadir, 'dst')
        self.temp = os.path.join(self.datadir, 'temp')
        Path.objects.create(entity='temp', value=self.temp)

        self.ip = InformationPackage.objects.create(object_path=self.dst, state='Prepared')
        self.baseurl = reverse('informationpackage-detail', args=(self.ip.pk,))

        self.org_group_type = GroupType.objects.create(label='organization')
        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.addCleanup(shutil.rmtree, self.datadir)

        for path in [self.src, self.dst, self.temp]:
            try:
                os.makedirs(path)
            except OSError as e:
                if e.errno != 17:
                    raise

    def test_upload_file(self):
        perms = {'group': ['view_informationpackage', 'ip.can_upload']}
        self.member.assign_object(self.group, self.ip, custom_permissions=perms)
        InformationPackage.objects.filter(pk=self.ip.pk).update(responsible=self.user)

        srcfile = os.path.join(self.src, 'foo.txt')
        srcfile_chunk = os.path.join(self.src, 'foo.txt_chunk')
        dstfile = os.path.join(self.dst, 'foo.txt')

        with open(srcfile, 'w') as fp:
            fp.write('bar')

        open(srcfile_chunk, 'a').close()

        fsize = os.path.getsize(srcfile)
        block_size = 1
        i = 0
        total = 0

        with open(srcfile, 'rb') as fp:
            while total < fsize:
                chunk = SimpleUploadedFile(srcfile_chunk, fp.read(block_size), content_type='multipart/form-data')
                data = {
                    'flowChunkNumber': i,
                    'flowRelativePath': os.path.basename(srcfile),
                    'file': chunk,
                }
                res = self.client.post(self.baseurl + 'upload/', data, format='multipart')
                self.assertEqual(res.status_code, status.HTTP_201_CREATED)
                total += block_size
                i += 1

        data = {'path': os.path.relpath(dstfile, self.dst)}
        res = self.client.post(self.baseurl + 'merge-uploaded-chunks/', data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        uploaded_chunks = glob.glob('%s_*' % dstfile)

        self.assertTrue(filecmp.cmp(srcfile, dstfile, False))
        self.assertEqual(uploaded_chunks, [])

    def test_upload_without_permission(self):
        perms = {'group': ['view_informationpackage']}
        self.member.assign_object(self.group, self.ip, custom_permissions=perms)

        srcfile = os.path.join(self.src, 'foo.txt')

        with open(srcfile, 'w') as fp:
            fp.write('bar')

        with open(srcfile, 'rb') as fp:
            chunk = SimpleUploadedFile(srcfile, fp.read(), content_type='multipart/form-data')
            data = {
                'flowChunkNumber': 0,
                'flowRelativePath': os.path.basename(srcfile),
                'file': chunk,
            }
            res = self.client.post(self.baseurl + 'upload/', data, format='multipart')
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_file_with_square_brackets_in_name(self):
        perms = {'group': ['view_informationpackage', 'ip.can_upload']}
        self.member.assign_object(self.group, self.ip, custom_permissions=perms)
        InformationPackage.objects.filter(pk=self.ip.pk).update(responsible=self.user)

        srcfile = os.path.join(self.src, 'foo[asd].txt')
        dstfile = os.path.join(self.dst, 'foo[asd].txt')

        with open(srcfile, 'w') as fp:
            fp.write('bar')

        with open(srcfile, 'rb') as fp:
            chunk = SimpleUploadedFile(srcfile, fp.read(), content_type='multipart/form-data')
            data = {
                'flowChunkNumber': 0,
                'flowRelativePath': os.path.basename(srcfile),
                'file': chunk,
            }
            self.client.post(self.baseurl + 'upload/', data, format='multipart')

            data = {'path': os.path.relpath(dstfile, self.dst)}
            self.client.post(self.baseurl + 'merge-uploaded-chunks/', data)

            self.assertTrue(filecmp.cmp(srcfile, dstfile, False))


class FilesActionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(label='organization')
        cls.user_role = GroupMemberRole.objects.create(codename='user_role')

    def setUp(self):
        self.root = self.datadir = tempfile.mkdtemp()
        self.datadir = os.path.join(self.root, 'datadir')
        self.addCleanup(shutil.rmtree, self.datadir)

        self.client = APIClient()
        self.user = User.objects.create(username="admin")
        self.ip = InformationPackage.objects.create(
            package_type=InformationPackage.SIP,
            object_path=self.datadir, responsible=self.user,
        )
        self.url = reverse('informationpackage-files', args=(self.ip.pk,))

        self.member = self.user.essauth_member

        self.org = Group.objects.create(name='organization', group_type=self.org_group_type)

        perms = Permission.objects.filter(codename='view_informationpackage')
        self.user_role.permissions.set(perms)

        membership = GroupMember.objects.create(member=self.member, group=self.org)
        membership.roles.add(self.user_role)

        self.org.add_object(self.ip)

        try:
            os.makedirs(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def test_get_method_with_no_params(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_get_method_with_no_pagination(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(self.url, data={'pager': 'none'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.get_path_response')
    def test_get_method_with_download_params_True(self, mock_ip_get_path_response):
        mock_ip_get_path_response.return_value = Response("dummy message")

        params = {'download': True}
        self.client.force_authenticate(user=self.user)
        self.client.get(self.url, params)

        mock_ip_get_path_response.assert_called_once_with(
            '',
            mock.ANY,
            force_download='True',
            paginator=mock.ANY
        )

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.get_path_response')
    def test_get_method_with_download_params_False(self, mock_ip_get_path_response):
        mock_ip_get_path_response.return_value = Response("dummy message")

        params = {'download': False}
        self.client.force_authenticate(user=self.user)
        self.client.get(self.url, params)

        mock_ip_get_path_response.assert_called_once_with(
            '',
            mock.ANY,
            force_download='False',
            paginator=mock.ANY
        )

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.get_path_response')
    def test_get_method_with_path_set(self, mock_ip_get_path_response):
        mock_ip_get_path_response.return_value = Response("dummy message")

        params = {'path': 'here_is_some/other_path'}
        self.client.force_authenticate(user=self.user)
        self.client.get(self.url, params)

        mock_ip_get_path_response.assert_called_once_with(
            'here_is_some/other_path',
            mock.ANY,
            force_download=False,
            paginator=mock.ANY
        )

    @mock.patch('ESSArch_Core.ip.models.InformationPackage.get_path_response')
    def test_get_method_with_path_set_with_extra_trailing_slash(self, mock_ip_get_path_response):
        mock_ip_get_path_response.return_value = Response("dummy message")

        params = {'path': 'here_is_some/other_path/'}
        self.client.force_authenticate(user=self.user)
        self.client.get(self.url, params)

        mock_ip_get_path_response.assert_called_once_with(
            'here_is_some/other_path',
            mock.ANY,
            force_download=False,
            paginator=mock.ANY
        )

    def test_post_method_when_ip_state_is_Prepared_and_path_parameter_not_set(self):
        self.ip.state = 'Prepared'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {}
        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['detail'], "Path parameter missing")

    def test_post_method_when_ip_state_is_Prepared_and_type_parameter_not_set(self):
        self.ip.state = 'Prepared'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {'path': 'dummy'}
        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['detail'], "Type parameter missing")

    def test_post_method_when_ip_state_is_Prepared_and_path_is_not_subdir_of_object_path(self):
        self.ip.state = 'Prepared'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {
            'path': tempfile.mkdtemp(),
            'type': 'dummy'
        }
        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['detail'], f"Illegal path {data['path']}")

    def test_post_method_when_ip_state_is_Prepared_and_path_type_is_not_dir_nor_file(self):
        self.ip.state = 'Prepared'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {
            'path': tempfile.mkdtemp(dir=self.datadir),
            'type': 'dummy'
        }

        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['detail'], 'Type must be either "file" or "dir"')

    def test_post_method_when_ip_state_is_Prepared_and_path_type_is_dir_and_already_exists(self):
        self.ip.state = 'Prepared'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {
            'path': tempfile.mkdtemp(dir=self.datadir),
            'type': 'dir'
        }

        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['detail'], f"Directory {data['path']} already exists")

    def test_post_method_when_ip_state_is_Prepared_and_path_type_is_dir(self):
        self.ip.state = 'Prepared'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {
            'path': os.path.join(self.datadir, 'some_dir_to_create'),
            'type': 'dir'
        }

        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data, data['path'])

    def test_post_method_when_ip_state_is_Prepared_and_path_type_is_file_and_already_exists(self):
        self.ip.state = 'Prepared'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        tmp_file_path = os.path.join(self.datadir, 'some_file')
        with open(tmp_file_path, 'a') as tmp_file:
            tmp_file.write("dummy")

        data = {
            'path': tmp_file_path,
            'type': 'file'
        }

        # Make sure file exists
        self.assertTrue(os.path.isfile(tmp_file_path))
        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data, data['path'])

    def test_post_method_when_ip_state_is_Prepared_and_path_type_is_file_and_it_doesnt_exist(self):
        self.ip.state = 'Prepared'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        tmp_file_path = os.path.join(self.datadir, 'some_file')

        data = {
            'path': tmp_file_path,
            'type': 'file'
        }

        # Make sure file does not exist
        self.assertFalse(os.path.isfile(tmp_file_path))
        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data, data['path'])

    def test_post_method_when_ip_state_is_Uploading_and_path_parameter_not_set(self):
        self.ip.state = 'Uploading'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {}
        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['detail'], "Path parameter missing")

    def test_post_method_when_ip_state_is_Uploading_and_type_parameter_not_set(self):
        self.ip.state = 'Uploading'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {'path': 'dummy'}
        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['detail'], "Type parameter missing")

    def test_post_method_when_ip_state_is_Uploading_and_path_is_not_subdir_of_object_path(self):
        self.ip.state = 'Uploading'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {
            'path': tempfile.mkdtemp(),
            'type': 'dummy'
        }
        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['detail'], f"Illegal path {data['path']}")

    def test_post_method_when_ip_state_is_Uploading_and_path_type_is_not_dir_nor_file(self):
        self.ip.state = 'Uploading'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {
            'path': tempfile.mkdtemp(dir=self.datadir),
            'type': 'dummy'
        }

        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['detail'], 'Type must be either "file" or "dir"')

    def test_post_method_when_ip_state_is_Uploading_and_path_type_is_dir_and_already_exists(self):
        self.ip.state = 'Uploading'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {
            'path': tempfile.mkdtemp(dir=self.datadir),
            'type': 'dir'
        }

        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['detail'], f"Directory {data['path']} already exists")

    def test_post_method_when_ip_state_is_Uploading_and_path_type_is_dir(self):
        self.ip.state = 'Uploading'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {
            'path': os.path.join(self.datadir, 'some_dir_to_create'),
            'type': 'dir'
        }

        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data, data['path'])

    def test_post_method_when_ip_state_is_Uploading_and_path_type_is_file_and_already_exists(self):
        self.ip.state = 'Uploading'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        tmp_file_path = os.path.join(self.datadir, 'some_file')
        with open(tmp_file_path, 'a') as tmp_file:
            tmp_file.write("dummy")

        data = {
            'path': tmp_file_path,
            'type': 'file'
        }

        # Make sure file exists
        self.assertTrue(os.path.isfile(tmp_file_path))
        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data, data['path'])

    def test_post_method_when_ip_state_is_Uploading_and_path_type_is_file_and_it_doesnt_exist(self):
        self.ip.state = 'Uploading'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        tmp_file_path = os.path.join(self.datadir, 'some_file')

        data = {
            'path': tmp_file_path,
            'type': 'file'
        }

        # Make sure file does not exist
        self.assertFalse(os.path.isfile(tmp_file_path))
        resp = self.client.post(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data, data['path'])

    def test_post_method_when_ip_state_is_not_Prepared_nor_Uploading(self):
        self.ip.state = 'some other state'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {}
        resp = self.client.post(self.url, data=data)

        expected_error_message = "Cannot delete or add content of an IP that is not in 'Prepared' or 'Uploading' state"
        self.assertEqual(resp.data['detail'], expected_error_message)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_method_when_ip_state_is_Prepared_and_path_does_not_exist(self):
        self.ip.state = 'Prepared'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {'path': 'some_path'}
        resp = self.client.delete(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp.data['detail'], "Path does not exist")

    def test_delete_method_when_ip_state_is_Prepared_and_path_parameter_does_not_exist(self):
        self.ip.state = 'Prepared'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {}
        resp = self.client.delete(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['detail'], "Path parameter missing")

    def test_delete_method_when_ip_state_is_Prepared_and_passed_path_is_not_subdir_of_object_path(self):
        self.ip.state = 'Prepared'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {'path': tempfile.mkdtemp()}
        resp = self.client.delete(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['detail'], f"Illegal path {data['path']}")

    def test_delete_method_when_ip_state_is_Prepared_and_passed_path_is_a_dir(self):
        self.ip.state = 'Prepared'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        tmp_dir_path = os.path.join(self.datadir, 'some_dir')
        os.makedirs(tmp_dir_path)
        data = {'path': tmp_dir_path}

        # Make sure file exists before deletion
        self.assertTrue(os.path.isdir(tmp_dir_path))
        resp = self.client.delete(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(os.path.exists(tmp_dir_path))

    def test_delete_method_when_ip_state_is_Prepared_and_passed_path_is_a_file(self):
        self.ip.state = 'Prepared'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        tmp_file_path = os.path.join(self.datadir, 'some_file')
        with open(tmp_file_path, 'a') as tmp_file:
            tmp_file.write("dummy")

        data = {'path': tmp_file_path}

        # Make sure file exists before deletion
        self.assertTrue(os.path.isfile(tmp_file_path))
        resp = self.client.delete(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(os.path.isfile(tmp_file_path))

    def test_delete_method_when_ip_state_is_Uploading_and_path_does_not_exist(self):
        self.ip.state = 'Uploading'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {'path': 'some_path'}
        resp = self.client.delete(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp.data['detail'], "Path does not exist")

    def test_delete_method_when_ip_state_is_Uploading_and_path_parameter_does_not_exist(self):
        self.ip.state = 'Uploading'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {}
        resp = self.client.delete(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['detail'], "Path parameter missing")

    def test_delete_method_when_ip_state_is_Uploading_and_passed_path_is_not_subdir_of_object_path(self):
        self.ip.state = 'Uploading'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {'path': tempfile.mkdtemp()}
        resp = self.client.delete(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['detail'], f"Illegal path {data['path']}")

    def test_delete_method_when_ip_state_is_Uploading_and_passed_path_is_a_dir(self):
        self.ip.state = 'Uploading'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        tmp_dir_path = os.path.join(self.datadir, 'some_dir')
        os.makedirs(tmp_dir_path)
        data = {'path': tmp_dir_path}

        # Make sure file exists before deletion
        self.assertTrue(os.path.isdir(tmp_dir_path))
        resp = self.client.delete(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(os.path.exists(tmp_dir_path))

    def test_delete_method_when_ip_state_is_Uploading_and_passed_path_is_a_file(self):
        self.ip.state = 'Uploading'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        tmp_file_path = os.path.join(self.datadir, 'some_file')
        with open(tmp_file_path, 'a') as tmp_file:
            tmp_file.write("dummy")

        data = {'path': tmp_file_path}

        # Make sure file exists before deletion
        self.assertTrue(os.path.isfile(tmp_file_path))
        resp = self.client.delete(self.url, data=data)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(os.path.isfile(tmp_file_path))

    def test_delete_method_when_ip_state_is_not_Prepared_nor_Uploading(self):
        self.ip.state = 'some other state'
        self.ip.save()
        self.client.force_authenticate(user=self.user)

        data = {}
        resp = self.client.delete(self.url, data=data)

        expected_error_message = "Cannot delete or add content of an IP that is not in 'Prepared' or 'Uploading' state"
        self.assertEqual(resp.data['detail'], expected_error_message)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
