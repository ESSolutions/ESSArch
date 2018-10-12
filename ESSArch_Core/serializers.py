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

from drf_dynamic_fields import DynamicFieldsMixin

from rest_framework import serializers


class DynamicHyperlinkedModelSerializer(DynamicFieldsMixin, serializers.HyperlinkedModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' and 'omit' args up to the superclass
        fields = kwargs.pop('fields', None)
        omit = kwargs.pop('omit', None)

        # Instantiate the superclass normally
        super(DynamicHyperlinkedModelSerializer, self).__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

        if omit is not None:
            # Drop any fields that are specified in the `omit` argument.
            disallowed = set(omit)
            existing = set(self.fields.keys())
            for field_name in existing & disallowed:
                self.fields.pop(field_name)
