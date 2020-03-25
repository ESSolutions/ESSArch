from django_filters import rest_framework as filters

from ESSArch_Core.maintenance.models import AppraisalJob, ConversionJob


class MaintenanceJobFilter(filters.FilterSet):
    end_date__isnull = filters.BooleanFilter(field_name='end_date', lookup_expr='isnull')

    class Meta:
        fields = ['start_date', 'end_date', 'status']


class AppraisalJobFilter(MaintenanceJobFilter):
    class Meta(MaintenanceJobFilter.Meta):
        model = AppraisalJob


class ConversionJobFilter(MaintenanceJobFilter):
    class Meta(MaintenanceJobFilter.Meta):
        model = ConversionJob
