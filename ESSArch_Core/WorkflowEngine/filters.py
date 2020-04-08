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

from django.db.models import Q
from django_filters import rest_framework as filters

from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask


class ProcessTaskFilter(filters.FilterSet):
    retry_type = filters.BooleanFilter(field_name='retry_type', method='filter_retry_type')
    retried = filters.BooleanFilter(method='filter_retried')
    hidden = filters.BooleanFilter(field_name='hidden', method='filter_hidden')

    def filter_hidden(self, queryset, name, value):
        if value is False:
            return queryset.filter(
                Q(Q(hidden=value) | Q(hidden__isnull=True)),
            )
        return queryset.filter(hidden=value)

    def filter_retry_type(self, queryset, name, value):
        value = not value
        return queryset.filter(retried_task__isnull=value)

    def filter_retried(self, queryset, name, value):
        value = not value
        return queryset.filter(retried__isnull=value)

    class Meta:
        model = ProcessTask
        fields = [
            'retry_type', 'hidden',
        ]


class ProcessStepFilter(filters.FilterSet):
    hidden = filters.BooleanFilter(field_name='hidden', method='filter_hidden')

    def filter_hidden(self, queryset, name, value):
        if value is False:
            return queryset.filter(
                Q(Q(hidden=value) | Q(hidden__isnull=True)),
            )
        return queryset.filter(hidden=value)

    class Meta:
        model = ProcessStep
        fields = [
            'hidden',
        ]
