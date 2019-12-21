import logging

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import (
    GroupAdmin as DjangoGroupAdmin,
    UserAdmin as DjangoUserAdmin,
)
from django.contrib.auth.models import Group as DjangoGroup
from django.db import transaction
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from groups_manager.models import (
    Group as GroupManagerGroup,
    GroupEntity,
    GroupMember as GroupManagerGroupMember,
    GroupMemberRole as GroupManagerGroupMemberRole,
    GroupType as GroupManagerGroupType,
    Member as GroupManagerMember,
)
from nested_inline.admin import NestedModelAdmin, NestedTabularInline
from rest_framework.authtoken.models import Token

from ESSArch_Core.admin import NestedStackedInlineWithoutHeader
from ESSArch_Core.auth.models import (
    Group,
    GroupMember,
    GroupMemberRole,
    GroupType,
    Member,
    ProxyGroup,
    ProxyPermission,
    ProxyUser,
)

csrf_protect_m = method_decorator(csrf_protect)
User = get_user_model()
logger = logging.getLogger('essarch.auth')

admin.site.unregister([
    GroupManagerMember,
    GroupManagerGroup,
    GroupManagerGroupMember,
    GroupEntity,
    GroupManagerGroupMemberRole,
    GroupManagerGroupType,
    SocialAccount,
    SocialApp,
    SocialToken,
])


def filter_permissions(qs):
    apps = ['groups_manager']
    excluded = Q(~Q(content_type__model='grouptype'), content_type__app_label__in=apps)
    return qs.exclude(excluded)


class GroupMemberForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expiration_date'].required = False
        self.fields['roles'].required = False
        self.fields['group'].disabled = True

    class Meta:
        model = GroupMember
        fields = '__all__'


class GroupMemberInline(NestedTabularInline):
    form = GroupMemberForm
    filter_horizontal = ['roles']
    fields = ['group', 'member', 'expiration_date', 'roles']
    model = GroupMember
    extra = 0
    verbose_name_plural = _('Assigned roles')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_module_permission(self, request):
        return True


class MemberInline(NestedStackedInlineWithoutHeader):
    model = Member
    exclude = ['username', 'first_name', 'last_name', 'email', 'django_auth_sync']
    inlines = [GroupMemberInline]
    fieldsets = (
        (None, {
            'fields': [],
            'description': _("Groups added above appears here when saving")
        }),
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_module_permission(self, request):
        return True


class UserAdmin(DjangoUserAdmin, NestedModelAdmin):
    add_form_template = 'essauth/admin/user/add_form.html'
    inlines = [MemberInline]
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Groups'), {'fields': ('groups',)})
    )

    def get_inline_instances(self, request, obj=None):
        if not request.user.has_perm("%s.%s" % ('essauth', 'assign_groupmemberrole')):
            return []

        return super().get_inline_instances(request, obj=obj)

    @csrf_protect_m
    @transaction.atomic
    def add_view(self, request, form_url='', extra_context=None):
        extra_context = self.admin_site.each_context(request)
        return super().add_view(request, form_url=form_url, extra_context=extra_context)

    @csrf_protect_m
    @transaction.atomic
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = self.admin_site.each_context(request)
        return super().change_view(request, object_id, form_url=form_url, extra_context=extra_context)

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == 'user_permissions':
            qs = kwargs.get('queryset', db_field.remote_field.model.objects)
            kwargs['queryset'] = filter_permissions(qs)
        return super().formfield_for_manytomany(
            db_field, request=request, **kwargs)

    def has_add_permission(self, request):
        return request.user.has_perm("%s.%s" % ('auth', 'add_user'))

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("%s.%s" % ('auth', 'change_user'))

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("%s.%s" % ('auth', 'delete_user'))

    def has_module_permission(self, request):
        return request.user.has_module_perms('auth')

    def log_addition(self, request, object, message):
        logger.info(f"User '{request.user}' attempts to add user '{object}' with msg: '{message}'.")

    def log_change(self, request, object, message):
        logger.info(f"User '{request.user}' attempts to change the user '{object}' with msg: '{message}'.")

    def log_deletion(self, request, object, message):
        logger.info(f"User '{request.user}' attempts to delete the user '{object}' with msg: '{message}'.")


class GroupForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['group_type'].required = False

    def save(self, commit=True):
        group = super().save(commit=False)
        group.name = group.django_group.name
        if commit:
            group.save()
            self._save_m2m()
        return group

    class Meta:
        model = Group
        fields = ['group_type', 'parent']


class GroupInline(admin.StackedInline):
    form = GroupForm
    model = Group

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_module_permission(self, request):
        return True


class GroupAdmin(DjangoGroupAdmin):
    add_form_template = 'essauth/admin/group/add_form.html'
    change_list_template = 'admin/mptt_change_list.html'
    inlines = [GroupInline]

    def get_ordering(self, request):
        """
        Changes the default ordering for changelists to tree-order.
        """
        mptt_opts = Group._mptt_meta
        return ('essauth_group__{}'.format(mptt_opts.tree_id_attr), 'essauth_group__{}'.format(mptt_opts.left_attr))

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == 'permissions':
            qs = kwargs.get('queryset', db_field.remote_field.model.objects)
            kwargs['queryset'] = filter_permissions(qs)
        return super().formfield_for_manytomany(
            db_field, request=request, **kwargs)

    def has_add_permission(self, request):
        return request.user.has_perm("%s.%s" % ('auth', 'add_group'))

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("%s.%s" % ('auth', 'change_group'))

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("%s.%s" % ('auth', 'delete_group'))

    def has_module_permission(self, request):
        return request.user.has_module_perms('auth')

    def log_addition(self, request, object, message):
        logger.info(f"User '{request.user}' attempts to add group '{object}' with msg: '{message}'.")

    def log_change(self, request, object, message):
        logger.info(f"User '{request.user}' attempts to change the group '{object}' with msg: '{message}'.")

    def log_deletion(self, request, object, message):
        logger.info(f"User '{request.user}' attempts to delete the group '{object}' with msg: '{message}'.")


class GroupTypeAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return request.user.has_perm("%s.%s" % ('groups_manager', 'add_grouptype'))

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("%s.%s" % ('groups_manager', 'change_grouptype'))

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("%s.%s" % ('groups_manager', 'delete_grouptype'))

    def has_module_permission(self, request):
        return request.user.has_module_perms('groups_manager')

    def log_addition(self, request, object, message):
        logger.info(f"User '{request.user}' attempts to create new group type '{object}' with msg: '{message}'.")

    def log_change(self, request, object, message):
        logger.info(f"User '{request.user}' attempts to change the group type '{object}' with msg: '{message}'.")

    def log_deletion(self, request, object, message):
        logger.info(f"User '{request.user}' attempts to delete the group type '{object}' with msg: '{message}'.")


class GroupMemberRoleAdmin(admin.ModelAdmin):
    filter_horizontal = ['permissions']
    exclude = ('label',)

    def log_addition(self, request, object, message):
        logger.info(f"User '{request.user}' attempts to create role '{object}' with msg: '{message}'.")

    def log_change(self, request, object, message):
        logger.info(f"User '{request.user}' attempts to change the role '{object}' with msg: '{message}'.")

    def log_deletion(self, request, object, message):
        logger.info(f"User '{request.user}' attempts to delete the role '{object}' with msg: '{message}'.")


class ProxyPermissionAdmin(admin.ModelAdmin):

    def log_addition(self, request, object, message):
        logger.info(f"User '{request.user}' attempts to create permission '{object.name}' with msg: '{message}'.")

    def log_change(self, request, object, message):
        logger.info(f"User '{request.user}' attempts to change the permission '{object.name}' with msg: '{message}'.")

    def log_deletion(self, request, object, message):
        logger.info(f"User '{request.user}' attempts to delete the permission '{object.name}' with msg: '{message}'.")


admin.site.unregister(DjangoGroup)
admin.site.unregister(EmailAddress)
admin.site.unregister(Token)
admin.site.unregister(User)
admin.site.register(ProxyPermission, ProxyPermissionAdmin)
admin.site.register(ProxyGroup, GroupAdmin)
admin.site.register(ProxyUser, UserAdmin)
admin.site.register(GroupType, GroupTypeAdmin)
admin.site.register(GroupMemberRole, GroupMemberRoleAdmin)
