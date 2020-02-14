from django_filters import rest_framework as filters

from ESSArch_Core.maintenance.models import (
    AppraisalJob,
    AppraisalTemplate,
    ConversionJob,
    ConversionTemplate,
)


class MaintenanceTemplateFilter(filters.FilterSet):
    related_to_ip = filters.CharFilter(method='filter_related_to_ip')
    not_related_to_ip = filters.CharFilter(method='filter_not_related_to_ip')

    def filter_related_to_ip(self, queryset, name, value):
        return queryset.filter(information_packages__id=value, information_packages__isnull=False)

    def filter_not_related_to_ip(self, queryset, name, value):
        return queryset.exclude(information_packages__id=value, information_packages__isnull=False)

    class Meta:
        fields = ['related_to_ip', 'not_related_to_ip']


class MaintenanceJobFilter(filters.FilterSet):
    end_date__isnull = filters.BooleanFilter(field_name='end_date', lookup_expr='isnull')

    class Meta:
        fields = ['start_date', 'end_date', 'status']


class AppraisalTemplateFilter(MaintenanceTemplateFilter):
    class Meta(MaintenanceTemplateFilter.Meta):
        model = AppraisalTemplate


class AppraisalJobFilter(MaintenanceJobFilter):
    class Meta(MaintenanceJobFilter.Meta):
        model = AppraisalJob


class ConversionTemplateFilter(MaintenanceTemplateFilter):
    class Meta(MaintenanceTemplateFilter.Meta):
        model = ConversionTemplate


class ConversionJobFilter(MaintenanceJobFilter):
    class Meta(MaintenanceJobFilter.Meta):
        model = ConversionJob
