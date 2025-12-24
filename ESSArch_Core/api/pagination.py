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

import hashlib

from django.conf import settings
from django.core.cache import caches
from django.core.paginator import EmptyPage
from django.db.models import F, Subquery
from django.db.models.query import QuerySet
from rest_framework import exceptions
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.utils.urls import remove_query_param, replace_query_param

DRF_CACHED_PAGINATION_COUNT_TIME = getattr(settings, 'DRF_CACHED_PAGINATION_COUNT_TIME', 0)


def CachedCountQueryset(queryset, timeout=DRF_CACHED_PAGINATION_COUNT_TIME, cache_name='default'):
    """
        Return copy of queryset with queryset.count() wrapped to cache result for `timeout` seconds.
    """
    if not isinstance(queryset, QuerySet):
        return queryset
    cache = caches[cache_name]
    queryset = queryset._chain()
    real_count = queryset.count

    def count(queryset):
        cache_key = 'query-count:' + hashlib.md5(str(queryset.query).encode('utf8')).hexdigest()

        # return existing value, if any
        value = cache.get(cache_key)
        if value is not None:
            # print('key: {} in cache with value: {}, real_value: {}'.format(cache_key, value, real_count()))
            return value

        # cache new value
        value = real_count()
        cache.set(cache_key, value, timeout)
        # print('key: {} not in cache with value: {}'.format(cache_key, value))
        return value
    # print('queryset: {}, type: {}'.format(str(queryset.query), repr(type(queryset))))
    queryset.count = count.__get__(queryset, type(queryset))
    return queryset


class LinkHeaderPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    after_query_param = 'after'
    after_field_query_param = 'after_field'

    def get_paginated_response(self, data):
        headers = {'Count': self.page.paginator.count}

        links = (
            ('next', self.get_next_link()),
            ('prev', self.get_previous_link()),
            ('first', self.get_first_link()),
            ('last', self.get_last_link()),
        )
        links = ['<{url}>; rel="{rel}"'.format(url=url, rel=rel) for rel, url in links if url is not None]
        if links:
            headers['Link'] = ', '.join(links)

        return Response(data, headers=headers)

    def get_first_link(self):
        if not self.page.has_previous():
            return None

        url = self.request.build_absolute_uri()
        return remove_query_param(url, self.page_query_param)

    def get_last_link(self):
        if not self.page.has_next():
            return None

        url = self.request.build_absolute_uri()
        return replace_query_param(url, self.page_query_param, self.page.paginator.num_pages)

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request

        after = request.query_params.get(self.after_query_param, None)
        after_field = request.query_params.get(self.after_field_query_param, None)

        if after is not None and after_field is None:
            raise exceptions.ParseError('"after_field" is required when using "after"')

        if after is not None:
            model = queryset.model
            current_filter = {after_field: after}
            after_filter = {'%s__lte' % after_field: F('current')}
            current = model.objects.filter(**current_filter)
            queryset = queryset.exclude(**current_filter)
            queryset = queryset.annotate(current=Subquery(current.values(after_field)[:1])).filter(**after_filter)

        if hasattr(queryset, 'count') and DRF_CACHED_PAGINATION_COUNT_TIME > 0:
            queryset = CachedCountQueryset(queryset)

        # --- DRF pagination with page clamping ---
        paginator = self.django_paginator_class(queryset, self.get_page_size(request))
        page_number = request.query_params.get(self.page_query_param, 1)

        try:
            self.page = paginator.page(page_number)
        except EmptyPage:
            # clamp to last page
            self.page = paginator.page(paginator.num_pages)

        self.paginator = paginator
        return list(self.page)


class NoPagination(PageNumberPagination):
    display_page_controls = False

    def get_page_size(self, request):
        return self.count if self.count > 0 else 1

    def paginate_queryset(self, queryset, request, view=None):
        try:
            self.count = queryset.count()
        except TypeError:
            if isinstance(queryset, list):
                self.count = len(queryset)
            else:
                raise

        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        headers = {'Count': self.count or 0}
        return Response(data, headers=headers)
