from django_filters import rest_framework as filters


from ESSArch_Core.maintenance.models import AppraisalJob, AppraisalRule, ConversionJob, ConversionRule

class AppraisalRuleFilter(filters.FilterSet):
    related_to_ip = filters.CharFilter(method='filter_related_to_ip')
    not_related_to_ip = filters.CharFilter(method='filter_not_related_to_ip')

    def filter_related_to_ip(self, queryset, name, value):
        return queryset.filter(information_packages__id=value, information_packages__isnull=False)

    def filter_not_related_to_ip(self, queryset, name, value):
        return queryset.exclude(information_packages__id=value, information_packages__isnull=False)

    class Meta:
        model = AppraisalRule
        fields = ['related_to_ip', 'not_related_to_ip']


class AppraisalJobFilter(filters.FilterSet):
    end_date__isnull = filters.BooleanFilter(name='end_date', lookup_expr='isnull')

    class Meta:
        model = AppraisalJob
        fields = ['start_date', 'end_date', 'status']


class ConversionRuleFilter(filters.FilterSet):
    related_to_ip = filters.CharFilter(method='filter_related_to_ip')
    not_related_to_ip = filters.CharFilter(method='filter_not_related_to_ip')

    def filter_related_to_ip(self, queryset, name, value):
        return queryset.filter(information_packages__id=value, information_packages__isnull=False)

    def filter_not_related_to_ip(self, queryset, name, value):
        return queryset.exclude(information_packages__id=value, information_packages__isnull=False)

    class Meta:
        model = ConversionRule
        fields = ['related_to_ip', 'not_related_to_ip']


class ConversionJobFilter(filters.FilterSet):
    end_date__isnull = filters.BooleanFilter(name='end_date', lookup_expr='isnull')

    class Meta:
        model = ConversionJob
        fields = ['start_date', 'end_date', 'status']
