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


class LinkHeaderPagination(pagination.PageNumberPagination):
    page_size_query_param = 'page_size'
    after_query_param = 'after'
    after_field_query_param = 'after_field'

    def get_paginated_response(self, data):
        headers = {'Count': self.page.paginator.count}

        next_url = self.get_next_link()
        previous_url = self.get_previous_link()

        if next_url is not None and previous_url is not None:
            link = '<{next_url}>; rel="next", <{previous_url}>; rel="prev"'
        elif next_url is not None:
            link = '<{next_url}>; rel="next"'
        elif previous_url is not None:
            link = '<{previous_url}>; rel="prev"'
        else:
            link = ''

        link = link.format(next_url=next_url, previous_url=previous_url)

        if link:
            headers['Link'] = link

        return Response(data, headers=headers)

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

        return super(LinkHeaderPagination, self).paginate_queryset(queryset, request, view)


class NoPagination(pagination.PageNumberPagination):
    display_page_controls = False

    def get_page_size(self, request):
        return self.count if self.count > 0 else 1

    def paginate_queryset(self, queryset, request, view=None):
        self.count = queryset.count()
        return super(NoPagination, self).paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        headers = {'Count': self.count or 0}
        return Response(data, headers=headers)
