from django_filters import rest_framework as filters

from ESSArch_Core.filters import ListFilter
from ESSArch_Core.ip.models import (
    ArchivalInstitution,
    ArchivistOrganization,
    ArchivalType,
    ArchivalLocation,
    EventIP,
)


class ArchivalInstitutionFilter(filters.FilterSet):
    ip_state = ListFilter(name='information_packages__state', distinct=True)

    class Meta:
        model = ArchivalInstitution
        fields = ('ip_state',)


class ArchivistOrganizationFilter(filters.FilterSet):
    ip_state = ListFilter(name='information_packages__state', distinct=True)

    class Meta:
        model = ArchivistOrganization
        fields = ('ip_state',)


class ArchivalTypeFilter(filters.FilterSet):
    ip_state = ListFilter(name='information_packages__state', distinct=True)

    class Meta:
        model = ArchivalType
        fields = ('ip_state',)


class ArchivalLocationFilter(filters.FilterSet):
    ip_state = ListFilter(name='information_packages__state', distinct=True)

    class Meta:
        model = ArchivalLocation
        fields = ('ip_state',)


class EventIPFilter(filters.FilterSet):
    eventDateTime = filters.DateTimeFromToRangeFilter()

    class Meta:
        model = EventIP
        fields = ('eventType', 'eventOutcome', 'linkingAgentRole', 'eventDateTime')
