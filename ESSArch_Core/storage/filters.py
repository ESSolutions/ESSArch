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

from django_filters import rest_framework as filters

from ESSArch_Core.api.filters import CharSuffixRangeFilter, ListFilter
from ESSArch_Core.configuration.models import StoragePolicy
from ESSArch_Core.storage.models import (
    STORAGE_TARGET_STATUS_ENABLED,
    STORAGE_TARGET_STATUS_MIGRATE,
    StorageMedium,
    StorageMethod,
    medium_type_CHOICES,
    storage_type_CHOICES,
)


class StorageMediumFilter(filters.FilterSet):
    status = ListFilter(field_name='status', distinct='true')
    medium_type = filters.ChoiceFilter(field_name='storage_target__type', choices=medium_type_CHOICES)
    storage_type = filters.ChoiceFilter(
        field_name='storage_target__storage_method_target_relations__storage_method__type',
        choices=storage_type_CHOICES
    )
    deactivatable = filters.BooleanFilter(label='deactivatable', method='filter_deactivatable')
    include_inactive_ips = filters.BooleanFilter(method='filter_include_inactive_ips')
    migratable = filters.BooleanFilter(label='migratable', method='filter_migratable')
    medium_id_range = CharSuffixRangeFilter(field_name='medium_id')
    policy = filters.ModelChoiceFilter(
        label='Policy', queryset=StoragePolicy.objects.all(),
        field_name='storage_target__storage_method_target_relations__storage_method__storage_policies',
        distinct=True
    )

    def filter_include_inactive_ips(self, queryset, *args):
        # this filter is only used together with deactivatable
        return queryset

    def filter_deactivatable(self, queryset, name, value):
        include_inactive_ips = self.request.query_params.get('include_inactive_ips', False)
        include_inactive_ips = include_inactive_ips in (True, 'True', 'true', '1')
        return queryset.deactivatable(include_inactive_ips=include_inactive_ips)

    def filter_migratable(self, queryset, name, value):
        if value:
            return queryset.migratable()
        else:
            return queryset.non_migratable()

    ordering = filters.OrderingFilter(
        fields=(
            ('id', 'id'),
            ('medium_id', 'medium_id'),
            ('storage_target__name', 'storage_target'),
            ('status', 'status'),
            ('location', 'location'),
            ('location_status', 'location_status'),
            ('used_capacity', 'used_capacity'),
            ('create_date', 'create_date'),
        ),
    )

    class Meta:
        model = StorageMedium
        fields = ('status', 'medium_type', 'storage_type', 'medium_id',)


class StorageMethodFilter(filters.FilterSet):
    policy = filters.ModelChoiceFilter(
        label='Policy', queryset=StoragePolicy.objects.all(),
        field_name='storage_policies',
        distinct=True
    )
    has_enabled_target = filters.BooleanFilter(method='filter_has_enabled_target')
    has_migrate_target = filters.BooleanFilter(method='filter_has_migrate_target')

    def filter_has_enabled_target(self, queryset, name, value):
        status = STORAGE_TARGET_STATUS_ENABLED
        return queryset.filter_has_target_with_status(status, value)

    def filter_has_migrate_target(self, queryset, name, value):
        status = STORAGE_TARGET_STATUS_MIGRATE
        return queryset.filter_has_target_with_status(status, value)

    class Meta:
        model = StorageMethod
        fields = ('enabled', 'policy', 'has_enabled_target', 'has_migrate_target',)
