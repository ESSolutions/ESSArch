from django.db.models import OuterRef, Subquery
from django_filters import rest_framework as filters

from ESSArch_Core.tags.models import Structure, StructureUnit, Tag


class StructureFilter(filters.FilterSet):
    archive = filters.UUIDFilter(method='filter_archive')
    latest_version = filters.BooleanFilter(label='latest version', method='filter_latest_version')

    def filter_archive(self, queryset, name, value):
        return queryset.filter(tagstructure__tag__versions__pk=value)

    def filter_latest_version(self, queryset, name, value):
        sub_query = queryset.filter(version_link=OuterRef('version_link'))\
            .order_by('-create_date')\
            .values('pk')[:1]

        if value:
            return queryset.filter(pk=Subquery(sub_query))
        else:
            return queryset.exclude(pk=Subquery(sub_query))

    class Meta:
        model = Structure
        fields = ['type', 'is_template', 'published', 'archive']


class StructureUnitFilter(filters.FilterSet):
    has_parent = filters.BooleanFilter(field_name='parent', lookup_expr='isnull', exclude=True)

    class Meta:
        model = StructureUnit
        fields = ['has_parent', 'structure']


class TagFilter(filters.FilterSet):
    index = filters.CharFilter(method='filter_index')

    ordering = filters.OrderingFilter(
        fields=(
            ('current_version__name', 'name'),
            ('current_version__start_date', 'start_date'),
            ('current_version__end_date', 'end_date'),
        ),
    )

    def filter_index(self, queryset, name, value):
        if value:
            return queryset.filter(versions__elastic_index=value)

        return queryset

    class Meta:
        model = Tag
        fields = ['index']
