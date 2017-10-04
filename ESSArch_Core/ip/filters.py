from django_filters import rest_framework as filters

from ESSArch_Core.ip.models import EventIP

class EventIPFilter(filters.FilterSet):
    eventDateTime = filters.DateTimeFromToRangeFilter()

    class Meta:
        model = EventIP
        fields = ('eventType', 'eventOutcome', 'linkingAgentRole', 'eventDateTime')
