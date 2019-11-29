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

import operator
import os
import re
from functools import reduce

import django_filters
from django.db import connection
from django.db.models import F, IntegerField, Q, UUIDField
from django.db.models.constants import LOOKUP_SEP
from django.db.models.functions import Cast, Substr
from django_filters import rest_framework as filters
from django_filters.constants import EMPTY_VALUES
from rest_framework.compat import distinct
from rest_framework.filters import (
    OrderingFilter,
    SearchFilter as DRFSearchFilter,
)

from ESSArch_Core.api.forms.fields import (
    CharSuffixRangeField,
    MultipleTextField,
)


def string_to_bool(s):
    if not isinstance(s, str):
        return None

    return {
        '1': True,
        '0': False,
        'true': True,
        'false': False,
    }.get(s.lower(), None)


class SearchFilter(DRFSearchFilter):
    """
    Workaround for filtering against UUIDFields
    when using database backends other than PostgreSQL.

    This can hopefully be removed when
    https://code.djangoproject.com/ticket/29915 is fixed
    """

    def filter_queryset(self, request, queryset, view):
        if connection.features.has_native_uuid_field:
            return super().filter_queryset(request, queryset, view)

        search_fields = self.get_search_fields(view, request)
        search_terms = self.get_search_terms(request)

        if not search_fields or not search_terms:
            return queryset

        orm_lookups = [
            self.construct_search(str(search_field))
            for search_field in search_fields
        ]

        base = queryset
        conditions = []
        for search_term in search_terms:
            queries = []

            for orm_lookup in orm_lookups:
                search_field = orm_lookup.split(LOOKUP_SEP)[0]
                field_type = queryset.model._meta.get_field(search_field)
                if isinstance(field_type, UUIDField):
                    search_term = search_term.replace('-', '')
                queries.append(Q(**{orm_lookup: search_term}))
            conditions.append(reduce(operator.or_, queries))
        queryset = queryset.filter(reduce(operator.and_, conditions))

        if self.must_call_distinct(queryset, search_fields):
            # Filtering against a many-to-many field requires us to
            # call queryset.distinct() in order to avoid duplicate items
            # in the resulting queryset.
            # We try to avoid this if possible, for performance reasons.
            queryset = distinct(queryset, base)
        return queryset


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


class CharSuffixRangeFilter(filters.RangeFilter):
    field_class = CharSuffixRangeField

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        if self.distinct:
            qs = qs.distinct()

        (start, start_suffix, start_suffix_pos) = value[0]
        (stop, stop_suffix, stop_suffix_pos) = value[1]

        suffix_pos = start_suffix_pos

        prefix_regex = r'^([\D|0]*)[0-9]*$'
        start_prefix = re.match(prefix_regex, start).group(1)
        stop_prefix = re.match(prefix_regex, stop).group(1)

        common_prefix = os.path.commonprefix([start_prefix, stop_prefix])

        if connection.vendor == 'microsoft':
            from sql_server.pyodbc.functions import TryCast
            cast_func = TryCast

            base = qs.filter(
                **{'{}__startswith'.format(self.field_name): common_prefix},
            ).annotate(
                suffix_string=Substr(F(self.field_name), suffix_pos + 1, len(start_suffix)),
            ).exclude(
                suffix_string__contains='%[^0-9]%',
            )
        else:
            cast_func = Cast

            base = qs.filter(
                **{'{}__regex'.format(self.field_name): r'{}[0-9]+$'.format(common_prefix)},
            )

        return base.annotate(
            suffix_number=cast_func(
                Substr(F(self.field_name), suffix_pos + 1, len(start_suffix)),
                IntegerField(),
            )
        ).filter(
            suffix_number__range=(start_suffix, stop_suffix),
        )


class UUIDInFilter(filters.BaseInFilter, filters.UUIDFilter):
    pass
