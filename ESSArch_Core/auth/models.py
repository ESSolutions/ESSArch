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

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as DjangoGroup, Permission
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import python_2_unicode_compatible
from django.db import models
from django.utils.translation import ugettext_lazy as _
from groups_manager import exceptions_gm
from groups_manager.models import GroupMixin, MemberMixin, GroupMemberMixin, GroupMemberRoleMixin, GroupType
from guardian.models import BaseGenericObjectPermission
from mptt.models import TreeForeignKey
from picklefield.fields import PickledObjectField

DjangoUser = get_user_model()


class GroupGenericObjects(models.Model):
    group = models.ForeignKey('essauth.Group', on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=255)
    content_object = GenericForeignKey()

    class Meta:
        unique_together = ['group', 'object_id', 'content_type']


@python_2_unicode_compatible
class GroupMemberRole(GroupMemberRoleMixin):
    codename = models.CharField(unique=True, max_length=255)
    label = models.SlugField(blank=True, max_length=255)
    permissions = models.ManyToManyField(Permission, related_name='roles')

    def __str__(self):
        return self.label

    def save(self, *args, **kwargs):
        if not self.label:
            self.label = self.codename
        super(GroupMemberRole, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'


class ProxyGroup(DjangoGroup):
    def save(self, *args, **kwargs):
        self.essauth_group.name = self.name
        self.essauth_group.save()
        super(ProxyGroup, self).save(*args, **kwargs)

    class Meta:
        verbose_name = _('group')
        verbose_name_plural = _('groups')
        proxy = True
        default_permissions = []


class ProxyUser(DjangoUser):
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        proxy = True
        default_permissions = []


class ProxyPermission(Permission):
    class Meta:
        verbose_name = _('permission')
        verbose_name_plural = _('permissions')
        proxy = True
        default_permissions = []


class Member(MemberMixin):
    django_user = models.OneToOneField(DjangoUser, null=False, on_delete=models.CASCADE,
                                       related_name='essauth_member')

    @property
    def full_name(self):
        return self.username

    @property
    def groups(self):
        return self.essauth_groups

    @property
    def group_model(self):
        return apps.get_model('essauth', 'Group')

    @property
    def group_member_model(self):
        return apps.get_model('essauth', 'GroupMember')

    class Meta(MemberMixin.Meta):
        abstract = False
        default_permissions = []


class GroupType(GroupType):
    class Meta:
        proxy = True
        default_permissions = []


class Group(GroupMixin):
    group_type = models.ForeignKey(GroupType, null=True, on_delete=models.SET_NULL,
                                   related_name='essauth_groups')

    django_group = models.OneToOneField(DjangoGroup, null=False, on_delete=models.CASCADE,
                                        related_name='essauth_group')
    group_members = models.ManyToManyField(Member, through='GroupMember',
                                           related_name='essauth_groups')
    parent = TreeForeignKey('self', null=True, blank=True,
                            related_name='sub_%(app_label)s_%(class)s_set')

    @property
    def member_model(self):
        return apps.get_model('essauth', 'Member')

    @property
    def group_member_model(self):
        return apps.get_model('essauth', 'GroupMember')

    @property
    def subgroups(self):
        return self.sub_essauth_group_set

    def add_object(self, obj):
        if getattr(self.group_type, 'codename') != 'organization':
            raise ValueError('objects cannot be added to non-organization groups')
        return GroupGenericObjects.objects.create(group=self, content_object=obj)

    def add_member(self, member, roles=None, expiration_date=None):
        """Add a member to the group.

        :Parameters:
          - `member`: member (required)
          - `roles`: list of roles. Each role could be a role id, a role label or codename,
            a role instance (optional, default: ``[]``)
          - `expiration_date`: A timestamp specifying when the membership
            expires. Note that this doesn't automatically remove the member
            from the group but is only an indicator to an external application
            to check if the membership still is valid
            (optional, default: ``None``)
        """
        if roles is None:
            roles = []
        if not self.id:
            raise exceptions_gm.GroupNotSavedError(
                "You must save the group before to create a relation with members")
        if not member.id:
            raise exceptions_gm.MemberNotSavedError(
                "You must save the member before to create a relation with groups")
        group_member_model = self.group_member_model
        group_member = group_member_model.objects.create(member=member, group=self, expiration_date=expiration_date)
        if roles:
            for role in roles:
                if isinstance(role, GroupMemberRole):
                    group_member.roles.add(role)
                elif isinstance(role, int):
                    role_obj = GroupMemberRole.objects.get(id=role)
                    group_member.roles.add(role_obj)
                else:
                    try:
                        role_obj = GroupMemberRole.objects.get(models.Q(label=role) |
                                                               models.Q(codename=role))
                        group_member.roles.add(role_obj)
                    except Exception as e:
                        raise exceptions_gm.GetRoleError(e)
        return group_member

    class Meta(GroupMixin.Meta):
        abstract = False
        default_permissions = []

    class MPTTMeta:
        level_attr = 'level'
        order_insertion_by = []


class GroupMember(GroupMemberMixin):
    group = models.ForeignKey(Group, related_name='group_membership', on_delete=models.CASCADE)
    member = models.ForeignKey(Member, related_name='group_membership', on_delete=models.CASCADE)
    roles = models.ManyToManyField(GroupMemberRole, related_name='group_memberships')
    expiration_date = models.DateTimeField(null=True, default=None)

    class Meta(GroupMemberMixin.Meta):
        unique_together = ('group', 'member')
        abstract = False
        default_permissions = []


class UserProfile(models.Model):
    DEFAULT_IP_LIST_COLUMNS = [
        'label', 'object_identifier_value', 'start_date', 'end_date', 'responsible',
        'state', 'step_state', 'status', 'filebrowser', 'delete',
    ]

    AIC = 'aic'
    IP = 'ip'
    IP_LIST_VIEW_CHOICES = (
        (AIC, 'AIC'),
        (IP, 'IP'),
    )

    user = models.OneToOneField(DjangoUser, on_delete=models.CASCADE, related_name='user_profile')
    current_organization = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)
    ip_list_columns = PickledObjectField(default=DEFAULT_IP_LIST_COLUMNS,)
    ip_list_view_type = models.CharField(max_length=10, choices=IP_LIST_VIEW_CHOICES, default=IP,)
    notifications_enabled = models.BooleanField(default=True)

    class Meta:
        db_table = "essauth_userprofile"


class NotificationManager(models.Manager):
    def create(self, **kwargs):
        refresh = kwargs.pop('refresh', False)
        notification = self.model(**kwargs)
        notification.refresh = refresh
        notification.save(force_insert=True)
        return notification


class Notification(models.Model):
    INFO = 10
    SUCCESS = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    LEVEL_CHOICES = (
        (INFO, 'info'),
        (SUCCESS, 'success'),
        (WARNING, 'warning'),
        (ERROR, 'error'),
        (CRITICAL, 'critical'),
    )

    user = models.ForeignKey(DjangoUser, on_delete=models.CASCADE, related_name='notifications')
    level = models.IntegerField(choices=LEVEL_CHOICES)
    message = models.CharField(max_length=255)
    time_created = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False)

    objects = NotificationManager()

    class Meta:
        ordering = ['-time_created']
        get_latest_by = "time_created"
        db_table = "essauth_notification"
