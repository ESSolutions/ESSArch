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

from django import forms
from django.contrib import admin

from .models import Profile, SubmissionAgreement
from .utils import profile_types


class SubmissionAgreementForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for pt in [pt.lower().replace(' ', '_') for pt in profile_types]:
            self.fields['profile_{}'.format(pt)].required = False

    class Meta:
        model = SubmissionAgreement
        fields = '__all__'


class SubmissionAgreementAdmin(admin.ModelAdmin):
    def render_change_form(self, request, context, *args, **kwargs):
        for pt in [pt.lower().replace(' ', '_') for pt in profile_types]:
            qs = Profile.objects.filter(profile_type=pt)
            context['adminform'].form.fields['profile_{}'.format(pt)].queryset = qs
        return super().render_change_form(request, context, args, kwargs)

    form = SubmissionAgreementForm
    list_display = ('name', 'type', 'status', 'label')
    search_fields = ('name', )
    readonly_fields = ('id',)
    list_filter = ('name', 'type')
    fieldsets = (
        (None, {
            'classes': ('wide'),
            'fields': ('id', 'name', 'type', 'status', 'label',)
        }),
        ('Information about Archival organization', {
            'classes': ('collapse', 'wide'),
            'fields': (
                'archivist_organization',
            )
        }),
        ('Profiles', {
            'classes': ('collapse', 'wide'),
            'fields': tuple(['profile_{}'.format(pt.lower().replace(' ', '_')) for pt in profile_types])
        }),
    )


admin.site.register(SubmissionAgreement, SubmissionAgreementAdmin)


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'status', 'label')
    search_fields = ('name', )
    readonly_fields = ('id',)
    list_filter = ('name', 'label')
    fieldsets = (
        (None, {
            'classes': ('wide'),
            'fields': (
                'id', 'profile_type', 'name', 'type', 'status', 'label',
                'representation_info', 'preservation_descriptive_info',
                'supplemental', 'access_constraints', 'datamodel_reference',
                'additional', 'submission_method', 'submission_schedule',
                'submission_data_inventory',
            )
        }),
        ('physical and logical structure', {
            'classes': ('collapse', 'wide'),
            'fields': ('structure',)
        }),
        ('form template', {
            'classes': ('collapse', 'wide'),
            'fields': ('template',)
        }),
        ('specification structure and data', {
            'classes': ('collapse', 'wide'),
            'fields': (
                'specification',
                'specification_data',
            )
        }),
    )


admin.site.register(Profile, ProfileAdmin)
