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

from django.db.models import F, Subquery
from rest_framework import exceptions, pagination
from rest_framework.response import Response
from rest_framework.utils.urls import remove_query_param, replace_query_param


class LinkHeaderPagination(pagination.PageNumberPagination):
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

        return super().paginate_queryset(queryset, request, view)


class NoPagination(pagination.PageNumberPagination):
    display_page_controls = False

    def get_page_size(self, request):
        return self.count if self.count > 0 else 1

    def paginate_queryset(self, queryset, request, view=None):
        self.count = queryset.count()
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        headers = {'Count': self.count or 0}
        return Response(data, headers=headers)
