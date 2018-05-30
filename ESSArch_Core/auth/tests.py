from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from groups_manager.utils import get_permission_name
from guardian.shortcuts import assign_perm

from ESSArch_Core.auth.models import Group, GroupType, GroupMemberRole
from ESSArch_Core.auth.util import get_objects_for_user
from ESSArch_Core.ip.models import InformationPackage


class OrganizationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member
        self.org_group_type = GroupType.objects.create(codename='organization')

    def test_user_current_organization_being_set_when_added_to_organization_group(self):
        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group.add_member(self.member)
        self.assertEqual(self.user.user_profile.current_organization, group)

        group2 = Group.objects.create(name='organization 2', group_type=self.org_group_type)
        group2.add_member(self.member)
        self.assertEqual(self.user.user_profile.current_organization, group)

    def test_user_current_organization_being_set_when_added_to_organization_group_indirectly(self):
        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group2 = Group.objects.create(name='child_group', parent=group)
        group2.add_member(self.member)

        self.assertEqual(self.user.user_profile.current_organization, group)

    def test_user_current_organization_is_changed_when_membership_is_removed(self):
        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group2 = Group.objects.create(name='organization 2', group_type=self.org_group_type)

        group.add_member(self.member)
        group2.add_member(self.member)

        group.remove_member(self.member)
        self.user.user_profile.refresh_from_db()
        self.assertEqual(self.user.user_profile.current_organization, group2)

        group2.remove_member(self.member)
        self.user.user_profile.refresh_from_db()
        self.assertEqual(self.user.user_profile.current_organization, None)


class OrganizationRoleTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member
        self.org_group_type = GroupType.objects.create(codename='organization')

        self.europe = Group.objects.create(name="europe", group_type=self.org_group_type)
        self.sweden = Group.objects.create(name="sweden", group_type=self.org_group_type, parent=self.europe)
        self.uppsala = Group.objects.create(name="uppsala", group_type=self.org_group_type, parent=self.sweden)
        self.sthlm = Group.objects.create(name="stockholm", group_type=self.org_group_type, parent=self.sweden)

        self.ctype = ContentType.objects.get_for_model(InformationPackage)
        self.user_perms = [Permission.objects.get_or_create(codename='view', content_type=self.ctype)[0]]
        self.admin_perms = [Permission.objects.get_or_create(codename='change', content_type=self.ctype)[0],
                            Permission.objects.get_or_create(codename='delete', content_type=self.ctype)[0]]
        self.expected_user_perms = ['view']
        self.expected_user_perms_with_label = ['ip.%s' % p for p in self.expected_user_perms]
        self.expected_admin_perms = ['change', 'delete']
        self.expected_admin_perms_with_label = ['ip.%s' % p for p in self.expected_admin_perms]

        self.admin_role = GroupMemberRole.objects.create(codename='admin')
        self.user_role = GroupMemberRole.objects.create(codename='user')
        self.user_role.permissions.add(*self.user_perms)
        self.admin_role.permissions.add(*self.admin_perms)

        # create users
        self.user_europe = User.objects.create(username='user_europe')
        self.admin_europe = User.objects.create(username='admin_europe')

        self.user_sweden = User.objects.create(username='user_sweden')
        self.admin_sweden = User.objects.create(username='admin_sweden')

        self.user_uppsala = User.objects.create(username='user_uppsala')
        self.admin_uppsala = User.objects.create(username='admin_uppsala')

        self.user_sthlm = User.objects.create(username='user_sthlm')
        self.admin_sthlm = User.objects.create(username='admin_sthlm')

        # add users to groups with roles
        self.europe.add_member(self.user_europe.essauth_member, roles=[self.user_role])
        self.europe.add_member(self.admin_europe.essauth_member, roles=[self.admin_role])

        self.sweden.add_member(self.user_sweden.essauth_member, roles=[self.user_role])
        self.sweden.add_member(self.admin_sweden.essauth_member, roles=[self.admin_role])

        self.uppsala.add_member(self.user_uppsala.essauth_member, roles=[self.user_role])
        self.uppsala.add_member(self.admin_uppsala.essauth_member, roles=[self.admin_role])

        self.sthlm.add_member(self.user_sthlm.essauth_member, roles=[self.user_role])
        self.sthlm.add_member(self.admin_sthlm.essauth_member, roles=[self.admin_role])

        # create IPs in organizations
        self.uppsala_ip = InformationPackage.objects.create()
        self.uppsala.add_object(self.uppsala_ip)

        self.sthlm_ip = InformationPackage.objects.create()
        self.sthlm.add_object(self.sthlm_ip)

    def test_get_permissions(self):
        self.assertItemsEqual(self.user_uppsala.get_all_permissions(), self.expected_user_perms_with_label)
        self.assertItemsEqual(self.admin_uppsala.get_all_permissions(), self.expected_admin_perms_with_label)
        self.assertItemsEqual(self.user_sweden.get_all_permissions(), self.expected_user_perms_with_label)
        self.assertItemsEqual(self.admin_sweden.get_all_permissions(), self.expected_admin_perms_with_label)

        # users in same organization as IP must have the correct permissions
        self.assertItemsEqual(self.user_uppsala.get_all_permissions(self.uppsala_ip), self.expected_user_perms)
        self.assertItemsEqual(self.admin_uppsala.get_all_permissions(self.uppsala_ip), self.expected_admin_perms)

        # users in an organization must have the correct permissions on the IPs in organizations/groups below
        self.assertItemsEqual(self.user_europe.get_all_permissions(self.uppsala_ip), self.expected_user_perms)
        self.assertItemsEqual(self.admin_europe.get_all_permissions(self.uppsala_ip), self.expected_admin_perms)

        self.assertItemsEqual(self.user_sweden.get_all_permissions(self.uppsala_ip), self.expected_user_perms)
        self.assertItemsEqual(self.admin_sweden.get_all_permissions(self.uppsala_ip), self.expected_admin_perms)

        self.assertItemsEqual(self.user_sweden.get_all_permissions(self.sthlm_ip), self.expected_user_perms)
        self.assertItemsEqual(self.admin_sweden.get_all_permissions(self.sthlm_ip), self.expected_admin_perms)

        # users in other organization than object must never have any permissions
        self.assertItemsEqual(self.user_uppsala.get_all_permissions(self.sthlm_ip), [])
        self.assertItemsEqual(self.admin_uppsala.get_all_permissions(self.sthlm_ip), [])

    def test_alter_role_permissions(self):
        # add permission to role
        self.user_perms.append(Permission.objects.get_or_create(codename='preserve', content_type=self.ctype)[0])
        self.user_role.permissions.set(self.user_perms)
        self.expected_user_perms.append('preserve')

        # delete permission from role
        self.admin_role.permissions.remove(Permission.objects.get(codename='delete', content_type=self.ctype))
        self.expected_admin_perms.remove('delete')

        self.assertItemsEqual(self.user_uppsala.get_all_permissions(self.uppsala_ip), self.expected_user_perms)
        self.assertItemsEqual(self.admin_uppsala.get_all_permissions(self.uppsala_ip), self.expected_admin_perms)

        self.assertItemsEqual(self.user_sthlm.get_all_permissions(self.uppsala_ip), [])
        self.assertItemsEqual(self.admin_sthlm.get_all_permissions(self.uppsala_ip), [])

        self.assertItemsEqual(self.user_sweden.get_all_permissions(self.sthlm_ip), self.expected_user_perms)
        self.assertItemsEqual(self.admin_sweden.get_all_permissions(self.sthlm_ip), self.expected_admin_perms)

    def test_permissions_added_for_new_groups(self):
        self.sthlm.add_member(self.user_uppsala.essauth_member, roles=[self.user_role])
        self.user_uppsala.user_profile.current_organization = self.sthlm
        self.user_uppsala.user_profile.save()

        self.assertItemsEqual(self.user_uppsala.get_all_permissions(self.uppsala_ip), self.expected_user_perms)
        self.assertItemsEqual(self.admin_uppsala.get_all_permissions(self.uppsala_ip), self.expected_admin_perms)

        self.assertItemsEqual(self.user_sthlm.get_all_permissions(self.uppsala_ip), [])
        self.assertItemsEqual(self.admin_sthlm.get_all_permissions(self.uppsala_ip), [])

        self.assertItemsEqual(self.user_uppsala.get_all_permissions(self.sthlm_ip), self.expected_user_perms)
        self.assertItemsEqual(self.admin_uppsala.get_all_permissions(self.sthlm_ip), [])

        self.assertItemsEqual(self.user_sweden.get_all_permissions(self.sthlm_ip), self.expected_user_perms)
        self.assertItemsEqual(self.admin_sweden.get_all_permissions(self.sthlm_ip), self.expected_admin_perms)

    def test_different_roles_at_different_levels(self):
        admin_uppsala_user_sweden = User.objects.create(username="admin_uppsala_user_sweden")
        self.uppsala.add_member(admin_uppsala_user_sweden.essauth_member, roles=[self.admin_role])
        self.sweden.add_member(admin_uppsala_user_sweden.essauth_member, roles=[self.user_role])
        admin_uppsala_user_sweden.user_profile.current_organization = self.uppsala
        admin_uppsala_user_sweden.user_profile.save()

        self.assertItemsEqual(admin_uppsala_user_sweden.get_all_permissions(self.sthlm_ip), self.expected_user_perms)
        self.assertItemsEqual(admin_uppsala_user_sweden.get_all_permissions(self.uppsala_ip), self.expected_user_perms + self.expected_admin_perms)

        self.assertItemsEqual(self.user_sweden.get_all_permissions(self.sthlm_ip), self.expected_user_perms)
        self.assertItemsEqual(self.user_sweden.get_all_permissions(self.uppsala_ip), self.expected_user_perms)

    def test_get_permissions_for_user_with_group_permissions(self):
        group_perm = Permission.objects.create(codename='group_perm', content_type=self.ctype)
        perms = {'group': [get_permission_name(group_perm, self.uppsala_ip)]}
        self.uppsala.assign_object(self.uppsala_ip, custom_permissions=perms)

        self.expected_user_perms.append('group_perm')
        self.assertItemsEqual(self.user_uppsala.get_all_permissions(self.uppsala_ip), self.expected_user_perms)
        self.assertItemsEqual(self.user_uppsala.get_all_permissions(self.sthlm_ip), [])

    def test_get_permissions_for_user_with_user_permissions(self):
        user_perm = Permission.objects.create(codename='user_perm', content_type=self.ctype)
        perm = get_permission_name(user_perm, self.uppsala_ip)
        assign_perm(perm, self.user_uppsala, self.uppsala_ip)

        self.expected_user_perms.append('user_perm')
        self.assertItemsEqual(self.user_uppsala.get_all_permissions(self.uppsala_ip), self.expected_user_perms)
        self.assertItemsEqual(self.user_uppsala.get_all_permissions(self.sthlm_ip), [])

    def test_get_objects_for_user(self):
        self.assertItemsEqual(list(get_objects_for_user(self.user_uppsala, InformationPackage, [])), [self.uppsala_ip])
        self.assertItemsEqual(list(get_objects_for_user(self.user_uppsala, InformationPackage, 'foo')), [])
        self.assertItemsEqual(list(get_objects_for_user(self.user_uppsala, InformationPackage, ['foo', self.expected_user_perms[0]])), [])
        self.assertItemsEqual(list(get_objects_for_user(self.user_uppsala, InformationPackage, self.expected_user_perms[0])), [self.uppsala_ip])
        self.assertItemsEqual(list(get_objects_for_user(self.user_uppsala, InformationPackage, self.expected_user_perms)), [self.uppsala_ip])

    def test_get_objects_for_user_with_group_permissions(self):
        group_perm = Permission.objects.create(codename='group_perm', content_type=self.ctype)
        perms = {'group': [get_permission_name(group_perm, self.uppsala_ip)]}
        self.uppsala.assign_object(self.uppsala_ip, custom_permissions=perms)

        self.assertItemsEqual(list(get_objects_for_user(self.user_uppsala, InformationPackage, ['foo'])), [])
        self.assertItemsEqual(list(get_objects_for_user(self.user_uppsala, InformationPackage, ['group_perm'])), [self.uppsala_ip])

    def test_get_objects_for_user_with_user_permissions(self):
        user_perm = Permission.objects.create(codename='user_perm', content_type=self.ctype)
        perm = get_permission_name(user_perm, self.uppsala_ip)
        assign_perm(perm, self.user_uppsala, self.uppsala_ip)

        self.assertItemsEqual(list(get_objects_for_user(self.user_uppsala, InformationPackage, ['foo'])), [])
        self.assertItemsEqual(list(get_objects_for_user(self.user_uppsala, InformationPackage, ['user_perm'])), [self.uppsala_ip])

    def test_get_objects_for_user_with_multiple_roles(self):
        admin_uppsala_user_sweden = User.objects.create(username="admin_uppsala_user_sweden")
        self.uppsala.add_member(admin_uppsala_user_sweden.essauth_member, roles=[self.admin_role])
        self.sweden.add_member(admin_uppsala_user_sweden.essauth_member, roles=[self.user_role])

        admin_uppsala_user_sweden.user_profile.current_organization = self.uppsala
        admin_uppsala_user_sweden.user_profile.save()

        self.assertItemsEqual(list(get_objects_for_user(admin_uppsala_user_sweden, InformationPackage, [])), [self.uppsala_ip])
        self.assertItemsEqual(list(get_objects_for_user(admin_uppsala_user_sweden, InformationPackage, 'foo')), [])
        self.assertItemsEqual(list(get_objects_for_user(admin_uppsala_user_sweden, InformationPackage, ['foo'] + self.expected_user_perms)), [])
        self.assertItemsEqual(list(get_objects_for_user(admin_uppsala_user_sweden, InformationPackage, self.expected_user_perms)), [self.uppsala_ip])
        self.assertItemsEqual(list(get_objects_for_user(admin_uppsala_user_sweden, InformationPackage, self.expected_admin_perms)), [self.uppsala_ip])
        self.assertItemsEqual(list(get_objects_for_user(admin_uppsala_user_sweden, InformationPackage, self.expected_user_perms + self.expected_admin_perms)), [self.uppsala_ip])

        admin_uppsala_user_sweden.user_profile.current_organization = self.sweden
        admin_uppsala_user_sweden.user_profile.save()

        self.assertItemsEqual(list(get_objects_for_user(admin_uppsala_user_sweden, InformationPackage, [])), [])
        self.assertItemsEqual(list(get_objects_for_user(admin_uppsala_user_sweden, InformationPackage, 'foo')), [])
        self.assertItemsEqual(list(get_objects_for_user(admin_uppsala_user_sweden, InformationPackage, ['foo'] + self.expected_user_perms)), [])
        self.assertItemsEqual(list(get_objects_for_user(admin_uppsala_user_sweden, InformationPackage, self.expected_user_perms)), [])
        self.assertItemsEqual(list(get_objects_for_user(admin_uppsala_user_sweden, InformationPackage, self.expected_admin_perms)), [])
        self.assertItemsEqual(list(get_objects_for_user(admin_uppsala_user_sweden, InformationPackage, self.expected_user_perms + self.expected_admin_perms)), [])
