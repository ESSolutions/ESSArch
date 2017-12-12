from django_filters import rest_framework as filters

from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation import AVAILABLE_VALIDATORS


class ValidationFilter(filters.FilterSet):
    validator = filters.CharFilter(method='filter_validator')
    passed = filters.BooleanFilter()

    def filter_validator(self, queryset, name, value):
        print name, value
        try:
            validator = AVAILABLE_VALIDATORS[value]
        except KeyError:
            return queryset.none()

        return queryset.filter(validator=validator.split('.')[-1])

    class Meta:
        model = Validation
        fields = ['filename', 'validator', 'passed', 'information_package']

