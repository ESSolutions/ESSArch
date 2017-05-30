#!/usr/bin/env /ESSArch/python27/bin/python
# -*- coding: UTF-8 -*-

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

from django.contrib import admin
import os

# own models ets
from .models import InformationPackage


def deleteIP(modeladmin, request, queryset):
    """
    An action for admin operations on IP
    """
    # if we have selected entryn
    if queryset.count():
        # delete files and directorys
        for obj in queryset:
            #ip_creator = "%s" % obj.creator
            for root, dirs, files in os.walk(obj.directory, topdown=False):
                for name in files:
                    #f = os.path.join(root, name)
                    #modeladmin.message_user(request, "filename '%s'" % (f))
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    #d = os.path.join(root, name)
                    #modeladmin.message_user(request, "dirname '%s'" % (d))
                    while True:
                        if not os.listdir(os.path.join(root, name)):
                            os.rmdir(os.path.join(root, name))
                            break

            while True:
                if not os.listdir(obj.directory):
                    os.rmdir(obj.directory)
                    break

            modeladmin.message_user(request, "Successfully deleted archivist organization '%s's archive '%s' in database and in directory '%s'" % (obj.archivist_organization, obj.label, obj.directory))

    # delete db entry
    queryset.delete()

deleteIP.short_description = "Delete selected ip from DB and FS"


class IPAdmin(admin.ModelAdmin):
    """
    Informaion Package
    """
    list_display = ('archivist_organization', 'label', 'create_date', 'id', 'object_path', 'state')
    search_fields = ('archivist_organization',)
    readonly_fields = ('id',)
    list_filter = ('archivist_organization', 'label')
    #fields = ('entity', 'value')
    fieldsets = (
                (None, {
                   'classes': ('wide'),
                   'fields': (
                              'id',
                              'label',
                              'content',
                              'responsible',
                              'create_date',
                              'state',
                              'status',
                              'object_path',
                              'start_date',
                              'end_date',
                              'package_type',
                              'submission_agreement',
                              'archival_institution',
                              'archivist_organization',
                              'archival_type',
                              'archival_location',
                             )}),
               )

admin.site.register(InformationPackage, IPAdmin)

