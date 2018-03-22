from django.contrib.auth.models import User
from django.test import TestCase

from groups_manager.models import GroupType

from ESSArch_Core.auth.models import Group, Member

class OrganizationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="admin")
        self.org_group_type = GroupType.objects.create(label='organization')

    def test_user_current_organization_being_set_when_added_to_organization_group(self):
        member = Member.objects.create(username=self.user.username, django_user=self.user)

        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group.add_member(member)
        self.assertEqual(self.user.user_profile.current_organization, group)

        group2 = Group.objects.create(name='organization 2', group_type=self.org_group_type)
        group2.add_member(member)
        self.assertEqual(self.user.user_profile.current_organization, group)

    def test_user_current_organization_being_set_when_added_to_organization_group_indirectly(self):
        member = Member.objects.create(username=self.user.username, django_user=self.user)
        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group2 = Group.objects.create(name='child_group', parent=group)
        group2.add_member(member)

        self.assertEqual(self.user.user_profile.current_organization, group)

    def test_user_current_organization_is_changed_when_membership_is_removed(self):
        member = Member.objects.create(username=self.user.username, django_user=self.user)
        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group2 = Group.objects.create(name='organization 2', group_type=self.org_group_type)

        group.add_member(member)
        group2.add_member(member)

        group.remove_member(member)
        self.user.user_profile.refresh_from_db()
        self.assertEqual(self.user.user_profile.current_organization, group2)

        group2.remove_member(member)
        self.user.user_profile.refresh_from_db()
        self.assertEqual(self.user.user_profile.current_organization, None)
