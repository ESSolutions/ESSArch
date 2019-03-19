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

from .models import Parameter, Path, EventType, Agent, Site
from django.contrib import admin
from django.contrib.sites.models import Site as DjangoSite


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


admin.site.unregister(DjangoSite)
admin.site.register(Agent, AgentAdmin)
admin.site.register(Site)
