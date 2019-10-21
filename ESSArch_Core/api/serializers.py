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

from django.utils.functional import cached_property
from drf_dynamic_fields import DynamicFieldsMixin
from languages_plus.models import Language
from rest_framework import serializers, validators


class DynamicModelSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    _dynamic_fields = None
    _dynamic_omitted = None

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        self._dynamic_fields = kwargs.pop('fields', None)
        self._dynamic_fields_omitted = kwargs.pop('omit', None)

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

    @cached_property
    def fields(self):
        fields = super().fields

        if self._dynamic_fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(self._dynamic_fields)
            existing = set(fields)
            for field_name in existing - allowed:
                fields.pop(field_name)

        if self._dynamic_fields_omitted is not None:
            # Drop any fields that are specified in the `omit` argument.
            disallowed = set(self._dynamic_fields_omitted)
            existing = set(fields)
            for field_name in existing & disallowed:
                fields.pop(field_name)

        return fields


class LanguageSerializer(serializers.ModelSerializer):
    id = serializers.CharField(
        source='iso_639_1', max_length=2,
        validators=[validators.UniqueValidator(queryset=Language.objects.all())],
    )

    class Meta:
        model = Language
        fields = ('id', 'name_en',)
