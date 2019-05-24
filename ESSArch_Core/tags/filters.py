from django.db.models import F

from django_filters import rest_framework as filters
from django_filters.widgets import BooleanWidget

from ESSArch_Core.tags.models import StructureUnit, Tag, TagVersion


class StructureUnitFilter(filters.FilterSet):
    has_parent = filters.BooleanFilter(field_name='parent', lookup_expr='isnull', exclude=True)

    class Meta:
        model = StructureUnit
        fields = ['has_parent']


class TagFilter(filters.FilterSet):
    index = filters.CharFilter(method='filter_index')

    def filter_index(self, queryset, name, value):
        if value:
            return queryset.filter(versions__elastic_index=value)

        return queryset

    class Meta:
        model = Tag
        fields = ['index']

class TagFilter(filters.FilterSet):
    include_leaves = filters.BooleanFilter(method='filter_leaves', widget=BooleanWidget())
    only_roots = filters.BooleanFilter(method='filter_roots', widget=BooleanWidget())
    all_versions = filters.BooleanFilter(method='filter_all_versions', widget=BooleanWidget())

    def filter_leaves(self, queryset, name, value):
        if not value:
            return queryset.exclude(lft=F('rght') - 1)

        return queryset

    def filter_roots(self, queryset, name, value):
        if value:
            return queryset.filter(parent__isnull=True)

        return queryset

    def filter_all_versions(self, queryset, name, value):
        if not value:
            return queryset.filter(tag__current_version=F('pk'))

        return queryset

    class Meta:
        model = TagVersion
        fields = ['include_leaves', 'elastic_index', 'all_versions']
