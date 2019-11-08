from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from groups_manager.utils import get_permission_name
from guardian.shortcuts import assign_perm

from ESSArch_Core.auth.models import Group, GroupMemberRole, GroupType
from ESSArch_Core.auth.util import (
    get_objects_for_user,
    get_user_groups,
    get_user_roles,
)
from ESSArch_Core.ip.models import InformationPackage

User = get_user_model()


class GetUserGroupsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member

    def test_no_groups_created(self):
        self.assertFalse(get_user_groups(self.user).exists())

    def test_no_groups_created_for_user(self):
        Group.objects.create()
        self.assertFalse(get_user_groups(self.user).exists())

    def test_group_created_for_user(self):
        grp = Group.objects.create()
        grp.add_member(self.member)

        self.assertEqual(get_user_groups(self.user).get(), grp)

    def test_multiple_groups_created_for_user(self):
        grp1 = Group.objects.create(name="1")
        grp2 = Group.objects.create(name="2")
        Group.objects.create(name="3")

        grp1.add_member(self.member)
        grp2.add_member(self.member)

        self.assertEqual(get_user_groups(self.user).count(), 2)

    def test_user_added_to_middle_group_of_tree(self):
        """
        With the following tree of groups:
           * Group 1
             * Group 2
               * Group 3
                 * Group 4
               * Group 5
             * Group 6

        If the user is added to "Group 2" they are also member of all groups
        below it, but not above it or adjacent to it.

        In this case it would be added to Group 2, 3, 4 and 5
        """

        grp1 = Group.objects.create(name="1")
        grp2 = Group.objects.create(name="2", parent=grp1)
        grp3 = Group.objects.create(name="3", parent=grp2)
        Group.objects.create(name="4", parent=grp3)
        Group.objects.create(name="5", parent=grp2)
        Group.objects.create(name="6", parent=grp1)

        grp2.add_member(self.member)

        self.assertEqual(list(get_user_groups(self.user).values_list('name', flat=True)), ['2', '3', '4', '5'])


class GetUserRolesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member
        self.org_group_type = GroupType.objects.create(label='organization')

    def test_no_groups_created(self):
        self.assertFalse(get_user_roles(self.user).exists())

    def test_no_groups_created_for_user(self):
        Group.objects.create()
        self.assertFalse(get_user_roles(self.user).exists())

    def test_non_organization_group_created_for_user_with_no_roles(self):
        grp = Group.objects.create()
        grp.add_member(self.member)

        self.assertFalse(get_user_roles(self.user).exists())

    def test_organization_group_created_for_user_with_no_roles(self):
        grp = Group.objects.create(group_type=self.org_group_type)
        grp.add_member(self.member)

        self.assertFalse(get_user_roles(self.user).exists())

    def test_non_organization_group_created_for_user_with_role(self):
        grp = Group.objects.create()
        role = GroupMemberRole.objects.create()
        grp.add_member(self.member, roles=[role])

        self.assertFalse(get_user_roles(self.user).exists())

    def test_organization_group_created_for_user_with_role(self):
        grp = Group.objects.create(group_type=self.org_group_type)
        role = GroupMemberRole.objects.create()
        grp.add_member(self.member, roles=[role])

        self.assertEqual(get_user_roles(self.user).get(), role)

    def test_only_roles_from_current_organization_is_returned(self):
        grp = Group.objects.create(name="1", group_type=self.org_group_type)
        grp2 = Group.objects.create(name="2", group_type=self.org_group_type)

        role1 = GroupMemberRole.objects.create(codename="1")
        role2 = GroupMemberRole.objects.create(codename="2")

        grp.add_member(self.member, roles=[role1])
        grp2.add_member(self.member, roles=[role2])

        self.assertEqual(get_user_roles(self.user).get(), role1)

        self.user.user_profile.current_organization = grp2
        self.user.user_profile.save()
        self.assertEqual(get_user_roles(self.user).get(), role2)

    def test_user_added_to_middle_group_of_tree(self):
        """
        With the following tree of groups:
           * Group 1
             * Group 2
               * Group 3
                 * Group 4
               * Group 5
             * Group 6

        If the user is added to "Group 2" they are also member of all groups
        below it. The role for their current organization are fetched from that
        organization and all organizations above it.

        I.e. if the user's current organization is "Group 3" the roles would be
        fetched from Group 1, 2 and 3
        """

        grp1 = Group.objects.create(name="1", group_type=self.org_group_type)
        grp2 = Group.objects.create(name="2", group_type=self.org_group_type, parent=grp1)
        grp3 = Group.objects.create(name="3", group_type=self.org_group_type, parent=grp2)
        grp4 = Group.objects.create(name="4", group_type=self.org_group_type, parent=grp3)
        grp5 = Group.objects.create(name="5", group_type=self.org_group_type, parent=grp2)
        grp6 = Group.objects.create(name="6", group_type=self.org_group_type, parent=grp1)

        role1 = GroupMemberRole.objects.create(codename="1")
        role2 = GroupMemberRole.objects.create(codename="2")
        role3 = GroupMemberRole.objects.create(codename="3")
        role4 = GroupMemberRole.objects.create(codename="4")
        role5 = GroupMemberRole.objects.create(codename="5")
        role6 = GroupMemberRole.objects.create(codename="6")

        grp1.add_member(self.member, roles=[role1])
        grp2.add_member(self.member, roles=[role2])
        grp3.add_member(self.member, roles=[role3])
        grp4.add_member(self.member, roles=[role4])
        grp5.add_member(self.member, roles=[role5])
        grp6.add_member(self.member, roles=[role6])

        self.user.user_profile.current_organization = grp3
        self.user.user_profile.save()
        self.assertCountEqual(list(get_user_roles(self.user).values_list('codename', flat=True)), ['1', '2', '3'])


class GetObjectsForUserTests(TestCase):
    def setUp(self):
        self.org_group_type = GroupType.objects.create(label='organization')
        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member

        content_type = ContentType.objects.get(app_label='ip', model='informationpackage')
        self.perm = Permission.objects.create(codename="view_object", content_type=content_type)

    def test_no_objects_created(self):
        qs = InformationPackage.objects.all()
        self.assertFalse(get_objects_for_user(self.user, qs, []).exists())

    def test_objects_without_any_permissions_available_for_all(self):
        InformationPackage.objects.create()
        qs = InformationPackage.objects.all()
        self.assertTrue(get_objects_for_user(self.user, qs, []).exists())

    def test_objects_added_to_user(self):
        ip = InformationPackage.objects.create()

        perm_name = get_permission_name('view_informationpackage', ip)
        assign_perm(perm_name, self.user, ip)

        qs = InformationPackage.objects.all()
        self.assertFalse(get_objects_for_user(self.user, qs, []).exists())
        self.assertEqual(get_objects_for_user(self.user, qs, ['view_informationpackage']).get(), ip)

    def test_objects_added_to_group(self):
        ip = InformationPackage.objects.create()

        group = Group.objects.create()
        group.add_member(self.member)

        perm_name = get_permission_name('view_informationpackage', ip)
        assign_perm(perm_name, group.django_group, ip)

        qs = InformationPackage.objects.all()
        self.assertFalse(get_objects_for_user(self.user, qs, []).exists())
        self.assertEqual(get_objects_for_user(self.user, qs, ['view_informationpackage']).get(), ip)

    def test_objects_added_to_parent_group(self):
        ip = InformationPackage.objects.create()

        parent = Group.objects.create(name='parent')
        group = Group.objects.create(parent=parent)
        group.add_member(self.member)

        perm_name = get_permission_name('view_informationpackage', ip)
        assign_perm(perm_name, parent.django_group, ip)

        qs = InformationPackage.objects.all()
        self.assertFalse(get_objects_for_user(self.user, qs, ['view_informationpackage']).exists())

    def test_objects_added_to_child_group(self):
        ip = InformationPackage.objects.create()

        parent = Group.objects.create(name='parent')
        parent.add_member(self.member)
        Group.objects.create(parent=parent)

        perm_name = get_permission_name('view_informationpackage', ip)
        assign_perm(perm_name, parent.django_group, ip)

        qs = InformationPackage.objects.all()
        self.assertEqual(get_objects_for_user(self.user, qs, ['view_informationpackage']).get(), ip)

    def test_objects_added_to_group_with_role(self):
        ip = InformationPackage.objects.create()
        perm = Permission.objects.get(codename='view_informationpackage')

        role = GroupMemberRole.objects.create(codename='ip_viewer')
        role.permissions.add(perm)

        group = Group.objects.create(group_type=self.org_group_type)
        group.add_member(self.member, roles=[role])
        group.add_object(ip)

        qs = InformationPackage.objects.all()
        self.assertFalse(get_objects_for_user(self.user, qs, ['non_existing_perm']).exists())
        self.assertTrue(get_objects_for_user(self.user, qs, []).exists())
        self.assertTrue(get_objects_for_user(self.user, qs, ['view_informationpackage']).exists())

    def test_all_objects_available_for_superuser(self):
        ip = InformationPackage.objects.create()
        self.user.is_superuser = True
        self.user.save()

        qs = InformationPackage.objects.all()
        self.assertEqual(get_objects_for_user(self.user, qs, ['view_informationpackage']).get(), ip)
