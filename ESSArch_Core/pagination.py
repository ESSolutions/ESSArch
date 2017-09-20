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

from rest_framework import pagination
from rest_framework.response import Response


class LinkHeaderPagination(pagination.PageNumberPagination):
    page_size_query_param = 'page_size'

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

class NoPagination(pagination.PageNumberPagination):
    display_page_controls = False

    def get_page_size(self, request):
        return self.count

    def paginate_queryset(self, queryset, request, view=None):
        self.count = queryset.count()
        return super(NoPagination, self).paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        headers = {'Count': len(data)}
        return Response(data, headers=headers)
