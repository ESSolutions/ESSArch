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

from django import forms
from django.contrib import admin
from django.utils.translation import ugettext as _
from nested_inline.admin import NestedStackedInline

from ESSArch_Core.storage.models import (
    STORAGE_TARGET_STATUS_ENABLED,
    TAPE,
    Robot,
    StorageMedium,
    StorageMethod,
    StorageMethodTargetRelation,
    StorageObject,
    StorageTarget,
    TapeDrive,
)


class StorageTargetInline(NestedStackedInline):
    """
    StorageTarget configuration
    """
    model = StorageMethodTargetRelation
    fk_name = 'storage_method'
    extra = 0
    fields = (
        'name',
        'status',
        'storage_target',
    )
    verbose_name = 'target relation'
    verbose_name_plural = ''

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        form = formset.form
        form.base_fields['storage_target'].widget.can_add_related = False
        form.base_fields['storage_target'].widget.can_change_related = False
        return formset


class StorageMethodTargetRelationInlineForm(forms.ModelForm):
    def clean_status(self):
        data = self.cleaned_data['status']
        if data == STORAGE_TARGET_STATUS_ENABLED:
            storage_method = self.instance.storage_method
            enabled_target = StorageMethodTargetRelation.objects.filter(
                storage_method=storage_method,
                status=STORAGE_TARGET_STATUS_ENABLED,
            ).first()

            if enabled_target != self.instance and enabled_target is not None:
                raise forms.ValidationError(
                    _('Only 1 target can be enabled for a storage method at a time'),
                    code='invalid',
                )
        return data


class StorageMethodTargetRelationInline(admin.TabularInline):
    """
    StorageMethodTargetRelation configuration
    """
    model = StorageMethod.targets.through
    form = StorageMethodTargetRelationInlineForm
    extra = 0


class StorageTargetsAdmin(admin.ModelAdmin):
    """
    StorageTargets configuration
    """
    list_display = ('name', 'target')
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


class StorageMediumAdmin(admin.ModelAdmin):
    exclude = (
        'create_date',
        'last_changed_local',
        'last_changed_external',
        'num_of_mounts',
        'used_capacity',
    )


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


class StorageObjectAdmin(admin.ModelAdmin):
    list_display = ('ip', 'storage_medium',)
    exclude = ('last_changed_local', 'last_changed_external',)


class TapeDriveAdmin(admin.ModelAdmin):
    exclude = ('last_change', 'num_of_mounts',)


admin.site.register(Robot)
admin.site.register(TapeDrive, TapeDriveAdmin)

admin.site.register(StorageMedium, StorageMediumAdmin)
admin.site.register(StorageMethod, StorageMethodAdmin)
admin.site.register(StorageObject, StorageObjectAdmin)
admin.site.register(StorageTarget, StorageTargetsAdmin)
