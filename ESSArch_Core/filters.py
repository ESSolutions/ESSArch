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

import django_filters
import six
from django_filters import rest_framework as filters
from django_filters.constants import EMPTY_VALUES
from django_filters.fields import IsoDateTimeField, RangeField
from django_filters.widgets import DateRangeWidget


def string_to_bool(s):
    if not isinstance(s, six.string_types):
        return None

    return {
        '1': True,
        '0': False,
        'true': True,
        'false': False,
    }.get(s.lower(), None)


class IsoDateTimeRangeField(RangeField):
    widget = DateRangeWidget

    def __init__(self, *args, **kwargs):
        fields = (IsoDateTimeField(), IsoDateTimeField())
        super(IsoDateTimeRangeField, self).__init__(fields, *args, **kwargs)


class IsoDateTimeFromToRangeFilter(filters.DateTimeFromToRangeFilter):
    field_class = IsoDateTimeRangeField


class ListFilter(django_filters.Filter):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('lookup_expr', 'in')
        super(ListFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        value_list = value.split(u',')
        return super(ListFilter, self).filter(qs, value_list)
