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
from django.utils.translation import ugettext as _

from ESSArch_Core.storage.models import (
    STORAGE_TARGET_STATUS_ENABLED,
    TAPE,
    Robot,
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
