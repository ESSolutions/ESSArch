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
from django.db.models import F
from django_filters import rest_framework as filters
from django_filters.constants import EMPTY_VALUES
from rest_framework.filters import OrderingFilter

from ESSArch_Core.api.forms.fields import MultipleTextField


def string_to_bool(s):
    if not isinstance(s, str):
        return None

    return {
        '1': True,
        '0': False,
        'true': True,
        'false': False,
    }.get(s.lower(), None)


class OrderingFilterWithNulls(OrderingFilter):
    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        ordered = []

        if ordering:
            for o in ordering:
                if not o:
                    continue
                if o[0] == '-':
                    ordered.append(F(o[1:]).desc(nulls_last=True))
                else:
                    ordered.append(F(o).asc(nulls_first=True))

        return queryset.order_by(*ordered)


class MultipleCharFilter(filters.MultipleChoiceFilter):
    field_class = MultipleTextField

    def filter(self, qs, value):
        if isinstance(value, list):
            value = [v for v in value if v not in EMPTY_VALUES]
        return super().filter(qs, value)


class ListFilter(django_filters.Filter):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('lookup_expr', 'in')
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        value_list = value.split(',')
        return super().filter(qs, value_list)
