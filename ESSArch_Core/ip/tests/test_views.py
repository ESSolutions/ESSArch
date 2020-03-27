import os
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from ESSArch_Core.auth.models import (
    Group,
    GroupMember,
    GroupMemberRole,
    GroupType,
)
from ESSArch_Core.configuration.models import Path, StoragePolicy
from ESSArch_Core.ip.models import InformationPackage, Workarea
from ESSArch_Core.profiles.models import SubmissionAgreement
from ESSArch_Core.storage.models import (
    DISK,
    STORAGE_TARGET_STATUS_ENABLED,
    STORAGE_TARGET_STATUS_MIGRATE,
    StorageMedium,
    StorageMethod,
    StorageMethodTargetRelation,
    StorageObject,
    StorageTarget,
)

User = get_user_model()


class WorkareaEntryViewSetTestCase(TestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

        Path.objects.create(entity="access_workarea", value=tempfile.mkdtemp(dir=self.datadir))
        Path.objects.create(entity="ingest_workarea", value=tempfile.mkdtemp(dir=self.datadir))
        temp_dir = Path.objects.create(entity='temp', value=tempfile.mkdtemp(dir=self.datadir)).value
        os.makedirs(os.path.join(temp_dir, 'file_upload'))

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
        aip2 = InformationPackage.objects.create(aic=aic, package_type=InformationPackage.AIP, generation=1)

        workarea = Workarea.objects.create(user=self.user, ip=aip, type=Workarea.ACCESS)
        workarea2 = Workarea.objects.create(user=self.user, ip=aip2, type=Workarea.ACCESS)

        os.makedirs(workarea.path)
        os.makedirs(workarea2.path)

        open(workarea.package_xml_path, 'a').close()
        open(workarea.aic_xml_path, 'a').close()
        open(workarea2.package_xml_path, 'a').close()

        self.org.add_object(aip)
        self.org.add_object(aip2)

        url = reverse('workarea-entries-detail', args=(str(workarea.pk),))
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        try:
            aip.refresh_from_db()
        except InformationPackage.DoesNotExist:
            self.fail("IP should not be deleted when read only workarea is deleted")

        self.assertFalse(os.path.exists(workarea.path))
        self.assertFalse(os.path.exists(workarea.package_xml_path))
        self.assertTrue(os.path.exists(workarea.aic_xml_path))
        self.assertTrue(os.path.exists(workarea2.path))
        self.assertTrue(os.path.exists(workarea2.package_xml_path))

        with self.assertRaises(Workarea.DoesNotExist):
            workarea.refresh_from_db()

        url = reverse('workarea-entries-detail', args=(str(workarea2.pk),))
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(os.path.exists(workarea2.aic_xml_path))
        self.assertFalse(os.path.exists(workarea2.path))
        self.assertFalse(os.path.exists(workarea2.package_xml_path))

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


class InformationPackageMigratableTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.storage_method = StorageMethod.objects.create()
        cls.storage_target = StorageTarget.objects.create()
        StorageMethodTargetRelation.objects.create(
            storage_method=cls.storage_method,
            storage_target=cls.storage_target,
            status=STORAGE_TARGET_STATUS_ENABLED
        )
        cls.storage_medium = StorageMedium.objects.create(
            storage_target=cls.storage_target,
            status=20, location_status=50, block_size=1024, format=103,
        )

        cls.policy = StoragePolicy.objects.create(
            cache_storage=cls.storage_method,
            ingest_path=Path.objects.create(entity='test', value='foo')
        )
        cls.policy.storage_methods.add(cls.storage_method)

        cls.sa = SubmissionAgreement.objects.create(policy=cls.policy)
        cls.ip = InformationPackage.objects.create(archived=True, submission_agreement=cls.sa)

    def test_get_migratable_no_change(self):
        StorageObject.objects.create(
            ip=self.ip, storage_medium=self.storage_medium,
            content_location_type=DISK,
        )
        ip_exists = InformationPackage.objects.migratable().exists()
        self.assertFalse(ip_exists)

    def test_get_migratable_new_storage_method(self):
        new_storage_method = StorageMethod.objects.create()
        new_storage_target = StorageTarget.objects.create(name='new')
        StorageMethodTargetRelation.objects.create(
            storage_method=new_storage_method,
            storage_target=new_storage_target,
            status=STORAGE_TARGET_STATUS_ENABLED
        )
        StorageObject.objects.create(
            ip=self.ip, storage_medium=self.storage_medium,
            content_location_type=DISK,
        )

        self.policy.storage_methods.add(new_storage_method)

        ip_exists = InformationPackage.objects.migratable().exists()
        self.assertTrue(ip_exists)

    def test_get_migratable_new_storage_target(self):
        # set the existing target as migratable
        StorageMethodTargetRelation.objects.update(
            status=STORAGE_TARGET_STATUS_MIGRATE
        )

        # the IP is not migratable until there is a new
        # enabled target available

        ip_exists = InformationPackage.objects.migratable().exists()
        self.assertFalse(ip_exists)

        # add a new enabled target

        new_storage_target = StorageTarget.objects.create(name='new')
        StorageMethodTargetRelation.objects.create(
            storage_method=self.storage_method,
            storage_target=new_storage_target,
            status=STORAGE_TARGET_STATUS_ENABLED
        )

        # its not relevant for this IP until the method contains it
        ip_exists = InformationPackage.objects.migratable().exists()
        self.assertFalse(ip_exists)

        # add IP to old method

        StorageObject.objects.create(
            ip=self.ip, storage_medium=self.storage_medium,
            content_location_type=DISK,
        )

        # the IP is now migratable to the new enabled target

        ip_exists = InformationPackage.objects.migratable().exists()
        self.assertTrue(ip_exists)

        # add object to new target

        storage_medium = StorageMedium.objects.create(
            medium_id='foo',
            storage_target=new_storage_target,
            status=20, location_status=50, block_size=1024, format=103,
        )
        StorageObject.objects.create(
            ip=self.ip, storage_medium=storage_medium,
            content_location_type=DISK,
        )

        # the IP is no longer migratable

        ip_exists = InformationPackage.objects.migratable().exists()
        self.assertFalse(ip_exists)
