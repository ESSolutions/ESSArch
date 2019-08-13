from django_filters import rest_framework as filters

from ESSArch_Core.configuration.models import EventType


class EventTypeFilter(filters.FilterSet):
    class Meta:
        model = EventType
        fields = ('category',)
