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
from django.contrib.sites.models import Site as DjangoSite
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from nested_inline.admin import NestedModelAdmin

from ESSArch_Core.configuration.models import ArchivePolicy
from ESSArch_Core.storage.admin import StorageMethodInline

from .models import Agent, EventType, Parameter, Path, Site

csrf_protect_m = method_decorator(csrf_protect)


class ParameterAdmin(admin.ModelAdmin):
    """
    Parameters for configuration options
    """
    list_display = ('entity', 'value')
    search_fields = ('entity',)
    fields = ('entity', 'value')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('entity',)

        return self.readonly_fields


admin.site.register(Parameter, ParameterAdmin)


class PathAdmin(admin.ModelAdmin):
    """
    Paths used for different operations
    """
    list_display = ('entity', 'value')
    search_fields = ('entity',)
    fields = ('entity', 'value')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('entity',)

        return self.readonly_fields


admin.site.register(Path, PathAdmin)


class EventTypeAdmin(admin.ModelAdmin):
    """
    Event types
    """
    list_display = ('eventDetail', 'eventType')
    search_fields = ('eventDetail',)


admin.site.register(EventType, EventTypeAdmin)


class AgentAdmin(admin.ModelAdmin):
    """
    Agents used for different operations
    """
    list_display = ('agentDetail', 'agentType')
    search_fields = ('agentDetail',)
    readonly_fields = ('agentDetail',)
    fields = ('agentType', 'agentDetail')


class ArchivePolicyAdmin(NestedModelAdmin):
    """
    ArchivePolicy
    """
    model = ArchivePolicy
    list_display = ('policy_name', 'policy_id', 'policy_stat', 'ais_project_name', 'ais_project_id', 'mode')
    fieldsets = (
        (None, {
            'fields': (
                'policy_stat',
                'policy_name',
                'policy_id',
                'ais_project_name',
                'ais_project_id',
                'mode',
                'checksum_algorithm',
                'ip_type',
                'preingest_metadata',
                'ingest_metadata',
                'information_class',
                'ingest_path',
                'cache_storage',
                'wait_for_approval',
                'validate_checksum',
                'validate_xml',
                'ingest_delete',
                'index',
                'receive_extract_sip',
                'cache_extracted_size',
                'cache_package_size',
                'cache_extracted_age',
                'cache_package_age',
            )
        }),
    )
    inlines = [StorageMethodInline]

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


admin.site.unregister(DjangoSite)
admin.site.register(Agent, AgentAdmin)
admin.site.register(Site)
admin.site.register(ArchivePolicy, ArchivePolicyAdmin)
