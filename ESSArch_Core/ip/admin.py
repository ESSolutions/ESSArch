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

import os
from os import walk

from django.contrib import admin

from .models import ConsignMethod, InformationPackage, OrderType


def deleteIP(modeladmin, request, queryset):
    """
    An action for admin operations on IP
    """
    # if we have selected entries
    if queryset.count():
        # delete files and directories
        for obj in queryset:
            for root, dirs, files in walk(obj.directory, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    while True:
                        if not os.listdir(os.path.join(root, name)):
                            os.rmdir(os.path.join(root, name))
                            break

            while True:
                if not os.listdir(obj.directory):
                    os.rmdir(obj.directory)
                    break

            modeladmin.message_user(
                request,
                "Successfully deleted archivist organization '%s's archive '%s' in database and in directory '%s'" % (
                    obj.archivist_organization, obj.label, obj.directory
                )
            )

    # delete db entry
    queryset.delete()


deleteIP.short_description = "Delete selected ip from DB and FS"


class IPAdmin(admin.ModelAdmin):
    """
    Information Package
    """
    list_display = ('label', 'id', 'object_path', 'package_type', 'state')
    readonly_fields = ('id',)
    search_fields = ['label', 'object_identifier_value', 'id']
    list_filter = ['state', ('state', admin.EmptyFieldListFilter),
                   'package_type']
    fieldsets = (
                (None, {
                    'classes': ('wide'),
                    'fields': (
                        'id',
                        'label',
                        'content',
                        'responsible',
                        'state',
                        'object_path',
                        'start_date',
                        'end_date',
                        'package_type',
                        'submission_agreement',
                    )}),
    )


admin.site.register(ConsignMethod)
admin.site.register(InformationPackage, IPAdmin)
admin.site.register(OrderType)
