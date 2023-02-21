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

import logging

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as DjangoGroup, Permission
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import (
    FieldDoesNotExist,
    MultipleObjectsReturned,
    ObjectDoesNotExist,
)
from django.db import models, transaction
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _
from groups_manager import exceptions_gm
from groups_manager.models import (
    GroupMemberMixin,
    GroupMemberRoleMixin,
    GroupMixin,
    GroupType,
    MemberMixin,
)
from mptt.models import TreeForeignKey
from picklefield.fields import PickledObjectField
from relativity.mptt import MPTTDescendants

DjangoUser = get_user_model()
logger = logging.getLogger('essarch.auth')


class BaseGenericObjects(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=255)
    content_object = GenericForeignKey()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]


class GroupObjectsManager(models.Manager):

    def is_generic(self):
        try:
            self.model._meta.get_field('object_id')
            # logger.debug('GroupObjects {} is using GenericForeignKey'.format(self.model._meta.object_name))
            return True
        except FieldDoesNotExist:
            # logger.debug('GroupObjects {} is using direct ForeignKey'.format(self.model._meta.object_name))
            return False

    def get_objects_for_group(self, group):
        objs = []
        if self.model.objects.is_generic():
            ctype = ContentType.objects.get_for_model(getattr(group, 'model', group))
            for go_obj in self.model.objects.filter(group=group, content_type=ctype):
                objs.append(go_obj.content_object)
        else:
            for go_obj in self.model.objects.filter(group=group):
                objs.append(go_obj.content_object)
        return objs

    def get_organization(self, obj, list=False):
        if self.model.objects.is_generic():
            ctype = ContentType.objects.get_for_model(getattr(obj, 'model', obj))
            if list:
                return self.model.objects.filter(object_id=obj.pk, content_type=ctype)
            else:
                return self.model.objects.get(object_id=obj.pk, content_type=ctype)
        else:
            if list:
                return self.model.objects.filter(content_object_id=obj.pk)
            else:
                return self.model.objects.get(content_object_id=obj.pk)

    def change_organization(self, obj, organization, force=False):
        if organization.group_type.codename != 'organization':
            raise ValueError('{} is not an organization'.format(organization))
        if isinstance(obj, list) or isinstance(obj, QuerySet):
            obj_list = obj
        else:
            obj_list = [obj]
        if self.model.objects.is_generic():
            # obj_list = list(obj_list)
            # logger.debug('Change org to {} for "generic" objs: {}'.format(organization, obj_list))
            ctype = ContentType.objects.get_for_model(getattr(obj, 'model', obj))
            for obj in obj_list:
                self.model.objects.update_or_create(object_id=obj.pk, content_type=ctype,
                                                    defaults={'group': organization})
        else:
            # obj_list = list(obj_list)
            # logger.debug('Change org to {} for "direct" objs: {}'.format(organization, obj_list))
            for obj in obj_list:
                try:
                    go_obj = self.model.objects.get(content_object_id=obj.pk)
                    go_obj.group = organization
                    go_obj.save()
                except ObjectDoesNotExist:
                    # message_info = 'GroupObjects for {} {} does not exists for organization: {}'.format(
                    #                                           obj._meta.model_name, obj, organization)
                    # logger.warning(message_info)
                    if force:
                        self.model.objects.create(content_object=obj, group=organization)
                except MultipleObjectsReturned as e:
                    go_objs = self.get_organization(obj, list=True)
                    group_list = [x.group for x in go_objs]
                    message_info = 'Expected one GroupObjects for {} {} but got multiple go_objs \
with folowing groups: {}'.format(obj._meta.model_name, obj, group_list)
                    logger.warning(message_info)
                    if force:
                        logger.warning('Change organiztion with force to {} for {} {}'.format(
                            organization, obj._meta.model_name, obj))
                        go_objs.delete()
                        self.model.objects.create(content_object=obj, group=organization)
                    else:
                        raise e


class GroupObjectsBase(models.Model):
    """
    **Manager**: :manager:`GroupObjectPermissionManager`
    """
    group = models.ForeignKey('essauth.Group', on_delete=models.CASCADE)

    objects = GroupObjectsManager()

    class Meta:
        abstract = True
        unique_together = ['group', 'content_object']


class GroupObjectsAbstract(GroupObjectsBase, BaseGenericObjects):

    class Meta(GroupObjectsBase.Meta, BaseGenericObjects.Meta):
        abstract = True
        unique_together = ['group', 'object_id']


class GroupGenericObjects(GroupObjectsAbstract):

    class Meta(GroupObjectsAbstract.Meta):
        abstract = False


class GroupMemberRole(GroupMemberRoleMixin):
    codename = models.CharField(_('name'), unique=True, max_length=255)
    label = models.SlugField(_('label'), blank=True, max_length=255)
    permissions = models.ManyToManyField(Permission, related_name='roles', blank=True, verbose_name=_('permissions'))
    external_id = models.CharField(_('external id'), max_length=255, blank=True, unique=True, null=True)

    def __str__(self):
        return self.label

    def save(self, *args, **kwargs):
        if not self.label:
            self.label = self.codename
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('role')
        verbose_name_plural = _('roles')
        permissions = (
            ('assign_groupmemberrole', 'Can assign roles'),
        )


class ProxyGroup(DjangoGroup):
    @transaction.atomic
    def save(self, *args, **kwargs):
        try:
            self.essauth_group.name = self.name
            self.essauth_group.save()
            return super().save(*args, **kwargs)
        except Group.DoesNotExist:
            group = super().save(*args, **kwargs)
            Group.objects.create(name=self.name, django_group=self)
            return group

    @property
    def tree_id(self):
        return self.essauth_group.tree_id

    @property
    def rght(self):
        return self.essauth_group.rght

    @property
    def lft(self):
        return self.essauth_group.lft

    @property
    def level(self):
        return self.essauth_group.level

    @property
    def parent(self):
        return self.essauth_group.parent

    @property
    def _mptt_meta(self):
        return Group._mptt_meta

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
        verbose_name = _('group type')
        verbose_name_plural = _('group types')
        proxy = True
        default_permissions = []


class Group(GroupMixin):
    group_type = models.ForeignKey(GroupType, null=True, on_delete=models.SET_NULL,
                                   related_name='essauth_groups', verbose_name=_('group type'))

    django_group = models.OneToOneField(DjangoGroup, null=False, on_delete=models.CASCADE,
                                        related_name='essauth_group')
    group_members = models.ManyToManyField(Member, through='GroupMember',
                                           related_name='essauth_groups')
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                            related_name='sub_%(app_label)s_%(class)s_set', verbose_name=_('parent'))
    external_id = models.CharField(_('external id'), max_length=255, blank=True, unique=True, null=True)
    properties = models.JSONField(_('properties'), default=dict, blank=True)

    descendants = MPTTDescendants()

    @property
    def member_model(self):
        return apps.get_model('essauth', 'Member')

    @property
    def group_member_model(self):
        return apps.get_model('essauth', 'GroupMember')

    @property
    def subgroups(self):
        return self.sub_essauth_group_set

    def get_users(self, subgroups=True):
        if subgroups:
            return DjangoUser.objects.filter(
                essauth_member__essauth_groups__in=self.get_descendants(include_self=True)
            )
        else:
            return DjangoUser.objects.filter(essauth_member__essauth_groups__=self)

    def add_object(self, obj):
        if self.group_type is None or self.group_type.codename != 'organization':
            raise ValueError('objects cannot be added to non-organization groups')
        from ESSArch_Core.auth.util import get_group_objs_model
        group_objs_model = get_group_objs_model(obj)
        kwargs = {'group': self}
        if group_objs_model.objects.is_generic():
            ctype = ContentType.objects.get_for_model(obj)
            kwargs['content_type'] = ctype
            kwargs['object_id'] = obj.pk
        else:
            kwargs['content_object'] = obj
        return group_objs_model.objects.get_or_create(**kwargs)

    def remove_object(self, obj):
        if self.group_type is None or self.group_type.codename != 'organization':
            raise ValueError('objects cannot be added to non-organization groups')
        from ESSArch_Core.auth.util import get_group_objs_model
        group_objs_model = get_group_objs_model(obj)
        kwargs = {'group': self}
        if group_objs_model.objects.is_generic():
            kwargs['object_id'] = obj.pk
        else:
            kwargs['content_object'] = obj
        return group_objs_model.objects.filter(**kwargs).delete()

    def add_user(self, user, roles=None, expiration_date=None):
        """Add a user to the group.

        :Parameters:
          - `user`: user (required)
          - `roles`: list of roles. Each role could be a role id, a role label or codename,
            a role instance (optional, default: ``[]``)
          - `expiration_date`: A timestamp specifying when the membership
            expires. Note that this doesn't automatically remove the member
            from the group but is only an indicator to an external application
            to check if the membership still is valid
            (optional, default: ``None``)
        """

        return self.add_member(user.essauth_member, roles=roles, expiration_date=expiration_date)

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
        group_member, _ = group_member_model.objects.get_or_create(
            member=member, group=self, expiration_date=expiration_date,
        )
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
        verbose_name = _('group')
        verbose_name_plural = _('groups')

    class MPTTMeta:
        level_attr = 'level'
        order_insertion_by = []


class GroupMember(GroupMemberMixin):
    group = models.ForeignKey(
        Group,
        related_name='group_membership',
        on_delete=models.CASCADE,
        verbose_name=_('group'),
    )
    member = models.ForeignKey(
        Member,
        related_name='group_membership',
        on_delete=models.CASCADE,
        verbose_name=_('member'),
    )
    roles = models.ManyToManyField(GroupMemberRole, related_name='group_memberships', verbose_name=_('roles'))
    expiration_date = models.DateTimeField(_('expiration date'), null=True, default=None)

    def __str__(self):
        return self.group.name

    class Meta(GroupMemberMixin.Meta):
        unique_together = ('group', 'member')
        abstract = False
        default_permissions = []


class UserProfile(models.Model):
    AIC = 'aic'
    IP = 'ip'
    FLAT = 'flat'
    IP_LIST_VIEW_CHOICES = (
        (AIC, 'AIC'),
        (IP, 'IP'),
        (FLAT, 'FLAT'),
    )

    LIST = 'list'
    GRID = 'grid'
    FILE_BROWSER_LIST_VIEW_CHOICES = (
        (LIST, 'list'),
        (GRID, 'grid'),
    )

    def default_ip_list_columns():
        return [
            'label', 'object_identifier_value', 'create_date', 'responsible',
            'state', 'step_state', 'status', 'filebrowser', 'delete',
        ]

    user = models.OneToOneField(DjangoUser, on_delete=models.CASCADE, related_name='user_profile')
    current_organization = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)
    language = models.CharField(max_length=10, default='')
    ip_list_columns = PickledObjectField(default=default_ip_list_columns)
    ip_list_view_type = models.CharField(max_length=10, choices=IP_LIST_VIEW_CHOICES, default=IP,)
    file_browser_view_type = models.CharField(max_length=10, choices=FILE_BROWSER_LIST_VIEW_CHOICES, default=LIST, )
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
