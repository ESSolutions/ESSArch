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

from .models import SubmissionAgreement, Profile
from .utils import profile_types

class SubmissionAgreementForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(SubmissionAgreementForm, self).__init__(*args, **kwargs)
        for pt in [pt.lower().replace(' ', '_') for pt in profile_types]:
            self.fields[u'profile_{}'.format(pt)].required = False

    class Meta:
        model = SubmissionAgreement
        fields = '__all__'


class SubmissionAgreementAdmin(admin.ModelAdmin):
    def render_change_form(self, request, context, *args, **kwargs):
        for pt in [pt.lower().replace(' ', '_') for pt in profile_types]:
            context['adminform'].form.fields[u'profile_{}'.format(pt)].queryset = Profile.objects.filter(profile_type=pt)
        return super(SubmissionAgreementAdmin, self).render_change_form(request, context, args, kwargs) 


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
        ('Change management', {
            'classes': ('collapse', 'wide'),
            'fields': (
                'cm_version', 'cm_release_date', 'cm_change_authority',
                'cm_change_description', 'cm_sections_affected'
            )
        }),
        ('Informaton about Producer organization', {
            'classes': ('collapse', 'wide'),
            'fields': (
                'producer_organization', 'producer_main_name',
                'producer_main_address', 'producer_main_phone',
                'producer_main_email', 'producer_main_additional',
                'producer_individual_name', 'producer_individual_role',
                'producer_individual_phone', 'producer_individual_email',
                'producer_individual_additional',
            )
        }),
        ('Information about Archival organization', {
            'classes': ('collapse', 'wide'),
            'fields': (
                'archivist_organization', 'archivist_main_name',
                'archivist_main_address', 'archivist_main_phone',
                'archivist_main_email', 'archivist_main_additional',
                'archivist_individual_name', 'archivist_individual_role',
                'archivist_individual_phone', 'archivist_individual_email',
                'archivist_individual_additional',
            )
        }),
        ('Information about designated community', {
            'classes': ('collapse', 'wide'),
            'fields': (
                'designated_community_description',
                'designated_community_individual_name',
                'designated_community_individual_role',
                'designated_community_individual_phone',
                'designated_community_individual_email',
                'designated_community_individual_additional',
            )
        }),
        ('Profiles', {
            'classes': ('collapse', 'wide'),
            'fields': tuple([u'profile_{}'.format(pt.lower().replace(' ', '_')) for pt in profile_types])
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
                'specification', 'specification_data',
            )
        }),
    )


admin.site.register(Profile, ProfileAdmin)
