from django_filters import rest_framework as filters
from rest_framework import exceptions

from ESSArch_Core.filters import IsoDateTimeFromToRangeFilter, ListFilter
from ESSArch_Core.ip.models import Agent, EventIP, InformationPackage, Workarea


class AgentFilter(filters.FilterSet):
    ip_state = ListFilter(name='information_packages__state', distinct=True)

    class Meta:
        model = Agent
        fields = ('ip_state',)


class InformationPackageFilter(filters.FilterSet):
    agents = ListFilter(name='agents__pk', label='Agent is in')
    archivist_organization = ListFilter(label='Archivist Organization is in', method='filter_archivist_organization')
    responsible = ListFilter(name='responsible__username')
    state = ListFilter(name='state')
    object_identifier_value = ListFilter(name='object_identifier_value')
    label = ListFilter(name='label')
    object_size = ListFilter(name='object_size')
    start_date = IsoDateTimeFromToRangeFilter()
    end_date = IsoDateTimeFromToRangeFilter()
    create_date = IsoDateTimeFromToRangeFilter()
    entry_date = IsoDateTimeFromToRangeFilter()

    def filter_archivist_organization(self, queryset, name, value):
        return queryset.filter(agents__role='ARCHIVIST', agents__type='ORGANIZATION', agents__name=value)

    class Meta:
        model = InformationPackage
        fields = ['agents', 'archivist_organization', 'state', 'label', 'object_identifier_value', 'responsible',
                  'create_date', 'entry_date', 'object_size', 'start_date', 'end_date']


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
