# -*- coding: UTF-8 -*-


from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group as DjangoGroup
from django.utils.translation import ugettext_lazy as _
from groups_manager.models import Group as GroupManagerGroup
from groups_manager.models import GroupEntity, GroupMemberRole, GroupType
from groups_manager.models import GroupMember as GroupManagerGroupMember
from groups_manager.models import Member as GroupManagerMember
from nested_inline.admin import NestedModelAdmin, NestedTabularInline

from ESSArch_Core.admin import NestedStackedInlineWithoutHeader
from ESSArch_Core.auth.models import (Group, GroupMember, Member, ProxyGroup,
                                      ProxyUser)

User = get_user_model()

admin.site.unregister(
    [GroupManagerMember, GroupManagerGroup, GroupManagerGroupMember, GroupEntity, GroupMemberRole, GroupType])


class GroupMemberForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(GroupMemberForm, self).__init__(*args, **kwargs)
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
    verbose_name_plural = 'Group settings'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class MemberInline(NestedStackedInlineWithoutHeader):
    model = Member
    exclude = ['username', 'first_name', 'last_name', 'email', 'django_auth_sync']
    inlines = [GroupMemberInline]
    fieldsets = (
        (None, {
            'fields': [],
            'description': "Groups added above appears here when saving"
        }),
    )

    def has_delete_permission(self, request, obj=None):
        return False


class UserAdmin(DjangoUserAdmin, NestedModelAdmin):
    add_form_template = 'essauth/admin/user/add_form.html'
    inlines = [MemberInline]
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        ('Groups', {'fields': ('groups',)})
    )


class GroupForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)
        self.fields['group_type'].required = False

    def save(self, commit=True):
        group = super(GroupForm, self).save(commit=False)
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


class GroupAdmin(DjangoGroupAdmin):
    inlines = [GroupInline]


admin.site.unregister(DjangoGroup)
admin.site.unregister(User)
admin.site.register(ProxyGroup, GroupAdmin)
admin.site.register(ProxyUser, UserAdmin)
