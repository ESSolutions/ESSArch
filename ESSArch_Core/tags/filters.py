from django_filters import rest_framework as filters

from ESSArch_Core.tags.models import StructureUnit, Tag


class StructureUnitFilter(filters.FilterSet):
    has_parent = filters.BooleanFilter(field_name='parent', lookup_expr='isnull', exclude=True)

    class Meta:
        model = StructureUnit
        fields = ['has_parent', 'structure']


class TagFilter(filters.FilterSet):
    index = filters.CharFilter(method='filter_index')

    def filter_index(self, queryset, name, value):
        if value:
            return queryset.filter(versions__elastic_index=value)

        return queryset

    class Meta:
        model = Tag
        fields = ['index']
