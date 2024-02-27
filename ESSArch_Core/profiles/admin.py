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
from django.db import models
from django_json_widget.widgets import JSONEditorWidget

from .models import Profile, SubmissionAgreement
from .utils import lowercase_profile_types_no_action_workflow


class SubmissionAgreementForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for pt in lowercase_profile_types_no_action_workflow:
            self.fields['profile_{}'.format(pt)].required = False

    class Meta:
        model = SubmissionAgreement
        fields = '__all__'


class SubmissionAgreementAdmin(admin.ModelAdmin):
    def render_change_form(self, request, context, *args, **kwargs):
        for pt in lowercase_profile_types_no_action_workflow:
            qs = Profile.objects.filter(profile_type=pt)
            context['adminform'].form.fields['profile_{}'.format(pt)].queryset = qs
        return super().render_change_form(request, context, args, kwargs)

    form = SubmissionAgreementForm
    list_display = ('name', 'label', 'type', 'status', 'published')
    search_fields = ('name', )
    readonly_fields = ('id',)
    list_filter = ('name', 'type')

    fieldsets = (
        (None, {
            'classes': ('wide'),
            'fields': (
                'id', 'name', 'label', 'type', 'status', 'published', 'archivist_organization',
                'overall_submission_agreement', 'policy',
            )
        }),
        ('form template', {
            'classes': ('collapse', 'wide'),
            'fields': ('template',)
        }),
        ('profiles', {
            'classes': ('collapse', 'wide'),
            'fields': tuple(['profile_{}'.format(pt) for pt in lowercase_profile_types_no_action_workflow])
        }),
    )
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }


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
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }


admin.site.register(Profile, ProfileAdmin)
