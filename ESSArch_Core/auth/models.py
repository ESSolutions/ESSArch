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
from django.contrib.auth.models import Group as DjangoGroup
from django.db import models
from django.utils.translation import ugettext_lazy as _
from groups_manager.models import GroupMixin, MemberMixin, GroupMemberMixin, GroupMemberRole, GroupType
from mptt.models import TreeForeignKey
from picklefield.fields import PickledObjectField

DjangoUser = get_user_model()


class ProxyGroup(DjangoGroup):
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


class Member(MemberMixin):
    django_user = models.OneToOneField(DjangoUser, null=False, on_delete=models.CASCADE,
                                       related_name='essauth_member')

    @property
    def full_name(self):
        return self.username

    @property
    def group_model(self):
        return apps.get_model('essauth', 'Group')

    @property
    def group_member_model(self):
        return apps.get_model('essauth', 'GroupMember')

    class Meta(MemberMixin.Meta):
        abstract = False


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

    class Meta(GroupMixin.Meta):
        abstract = False


class GroupMember(GroupMemberMixin):
    group = models.ForeignKey(Group, related_name='group_membership', on_delete=models.CASCADE)
    member = models.ForeignKey(Member, related_name='group_membership', on_delete=models.CASCADE)
    roles = models.ManyToManyField(GroupMemberRole, related_name='group_memberships')
    expiration_date = models.DateTimeField(null=True, default=None)

    class Meta(GroupMemberMixin.Meta):
        unique_together = ('group', 'member')
        abstract = False


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
