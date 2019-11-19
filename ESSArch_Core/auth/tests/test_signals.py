from django.contrib.auth.models import User
from django.test import TestCase

from ESSArch_Core.auth.models import Group, GroupType


class CurrentOrganizationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member
        self.org_group_type = GroupType.objects.create(codename='organization')

    def test_set_when_added_to_organization_group(self):
        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group.add_member(self.member)
        self.assertEqual(self.user.user_profile.current_organization, group)

        group2 = Group.objects.create(name='organization 2', group_type=self.org_group_type)
        group2.add_member(self.member)
        self.assertEqual(self.user.user_profile.current_organization, group)

    def test_set_when_added_to_organization_group_indirectly(self):
        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group2 = Group.objects.create(name='child_group', parent=group)
        group2.add_member(self.member)

        self.assertEqual(self.user.user_profile.current_organization, group)

    def test_changed_when_membership_is_removed(self):
        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group2 = Group.objects.create(name='organization 2', group_type=self.org_group_type)

        group.add_member(self.member)
        group2.add_member(self.member)

        group.remove_member(self.member)
        self.user.user_profile.refresh_from_db()
        self.assertEqual(self.user.user_profile.current_organization, group2)

        group2.remove_member(self.member)
        self.user.user_profile.refresh_from_db()
        self.assertIsNone(self.user.user_profile.current_organization)
