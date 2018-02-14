from django_filters import rest_framework as filters

from rest_framework import exceptions

from ESSArch_Core.filters import IsoDateTimeFromToRangeFilter, ListFilter
from ESSArch_Core.ip.models import (
    ArchivalInstitution,
    ArchivistOrganization,
    ArchivalType,
    ArchivalLocation,
    EventIP,
    InformationPackage,
    Workarea,
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


class InformationPackageFilter(filters.FilterSet):
    responsible = ListFilter(name='responsible__username')
    create_date = IsoDateTimeFromToRangeFilter()
    state = ListFilter(name='state')

    class Meta:
        model = InformationPackage
        fields = [
            'create_date', 'state', 'archival_institution', 'archivist_organization',
            'archival_type', 'archival_location', 'responsible',
        ]


class EventIPFilter(filters.FilterSet):
    eventDateTime = IsoDateTimeFromToRangeFilter()

    class Meta:
        model = EventIP
        fields = ('eventType', 'eventOutcome', 'linkingAgentRole', 'eventDateTime')

class WorkareaEntryFilter(filters.FilterSet):
    type = filters.CharFilter(method='filter_type')

    class Meta:
        model = Workarea
        fields = ('type', 'user', 'read_only',)

    def filter_type(self, queryset, name, value):
        workarea_type_reverse = dict((v.lower(), k) for k, v in Workarea.TYPE_CHOICES)

        try:
            workarea_type = workarea_type_reverse[value]
        except KeyError:
            raise exceptions.ParseError('Workarea of type "%s" does not exist' % value)

        return queryset.filter(**{name: workarea_type})
