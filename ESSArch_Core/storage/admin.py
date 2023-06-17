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

from django import forms
from django.contrib import admin
from django.utils.translation import gettext as _

from ESSArch_Core.storage.models import (
    STORAGE_TARGET_STATUS_ENABLED,
    TAPE,
    Robot,
    RobotQueue,
    StorageMedium,
    StorageMethod,
    StorageObject,
    StorageTarget,
    TapeDrive,
)


class StorageMethodTargetRelationInlineFormSet(forms.models.BaseInlineFormSet):
    def clean(self):
        enabled = False
        for form in self.forms:
            if form.cleaned_data.get('status') == STORAGE_TARGET_STATUS_ENABLED:
                if enabled:
                    raise forms.ValidationError(
                        _('Only 1 target can be enabled for a storage method at a time'),
                        code='invalid',
                    )

                enabled = True


class StorageMethodTargetRelationInline(admin.TabularInline):
    """
    StorageMethodTargetRelation configuration
    """
    model = StorageMethod.targets.through
    formset = StorageMethodTargetRelationInlineFormSet
    extra = 0


class StorageTargetsAdmin(admin.ModelAdmin):
    """
    StorageTargets configuration
    """
    list_display = ('name', 'target', 'type', 'status')
    sortable_field_name = "name"
    fieldsets = (
        (None, {
            'fields': (
                'name',
                'status',
                'type',
                'default_block_size',
                'default_format',
                'min_chunk_size',
                'min_capacity_warning',
                'max_capacity',
                'remote_server',
                'master_server',
                'target',
            )
        }),
    )


class StorageMediumInRobotListFilter(admin.SimpleListFilter):
    title = _("Robot slot")
    parameter_name = "robot_slot"

    def lookups(self, request, model_admin):
        return [
            ('1', _("Yes")),
            ('0', _("No")),
        ]

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(
                tape_slot__isnull=False
            )
        if self.value() == '0':
            return queryset.filter(
                tape_slot__isnull=True
            )


class StorageMediumAdmin(admin.ModelAdmin):
    list_display = ('medium_id', 'storage_target', 'location', 'status')
    exclude = (
        'create_date',
        'last_changed_local',
        'last_changed_external',
        'num_of_mounts',
        'used_capacity',
    )
    search_fields = ['medium_id']
    list_filter = [StorageMediumInRobotListFilter]


class StorageMethodAdminForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        storage_type = cleaned_data.get('type')
        containers = cleaned_data.get('containers')

        if storage_type == TAPE and not containers:
            raise forms.ValidationError('Tapes can only be used for containers')


class StorageMethodAdmin(admin.ModelAdmin):
    form = StorageMethodAdminForm
    list_display = ('name', 'enabled', 'type', 'containers',)
    exclude = ('storage_policies',)
    inlines = [StorageMethodTargetRelationInline]


class StorageObjectInRobotListFilter(admin.SimpleListFilter):
    title = _("Robot slot")
    parameter_name = "robot_slot"

    def lookups(self, request, model_admin):
        return [
            ('1', _("Yes")),
            ('0', _("No")),
        ]

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(
                storage_medium__tape_slot__isnull=False
            )
        if self.value() == '0':
            return queryset.filter(
                storage_medium__tape_slot__isnull=True
            )


class StorageObjectAdmin(admin.ModelAdmin):
    list_display = ('ip', 'content_location_value', 'storage_medium',)
    exclude = ('last_changed_local', 'last_changed_external',)
    # search_fields = ['ip', 'storage_medium']
    search_fields = ['ip__object_identifier_value', 'storage_medium__medium_id']
    list_filter = [StorageObjectInRobotListFilter]


class TapeDriveAdmin(admin.ModelAdmin):
    list_display = ('device', 'drive_id', 'robot', 'locked_by', 'status')
    exclude = ('last_change', 'num_of_mounts')
    readonly_fields = ["locked_by"]
    actions = ["clear_lock"]

    @admin.action(permissions=["change"], description=_("Clear lock for selected drives"))
    def clear_lock(self, request, queryset):
        for obj in queryset:
            obj.clear_lock()


class RobotAdmin(admin.ModelAdmin):
    list_display = ('label', 'device', 'online')


class RobotQueueAdmin(admin.ModelAdmin):
    list_display = ('id', 'posted', 'req_type', 'storage_medium', 'status')


admin.site.register(Robot, RobotAdmin)
admin.site.register(RobotQueue, RobotQueueAdmin)
admin.site.register(TapeDrive, TapeDriveAdmin)

admin.site.register(StorageMedium, StorageMediumAdmin)
admin.site.register(StorageMethod, StorageMethodAdmin)
admin.site.register(StorageObject, StorageObjectAdmin)
admin.site.register(StorageTarget, StorageTargetsAdmin)
