from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from rest_framework import exceptions

from ESSArch_Core.api.filters import ListFilter, MultipleCharFilter
from ESSArch_Core.auth.util import users_in_organization
from ESSArch_Core.configuration.models import StoragePolicy
from ESSArch_Core.ip.models import Agent, EventIP, InformationPackage, Workarea
from ESSArch_Core.storage.models import StorageMedium
from ESSArch_Core.util import strtobool

User = get_user_model()


def states():
    result = InformationPackage.objects.order_by().values_list('state', flat=True)
    return [(state, state.capitalize()) for state in result]


class AgentFilter(filters.FilterSet):
    ip_state = ListFilter(field_name='information_packages__state', distinct=False)

    class Meta:
        model = Agent
        fields = ('ip_state',)


class InformationPackageFilter(filters.FilterSet):
    archivist_organization = filters.ModelMultipleChoiceFilter(
        label=_("Archivist Organization"),
        queryset=Agent.objects.filter(role__iexact="archivist", type__iexact="organization"),
    )
    responsible = filters.ModelMultipleChoiceFilter(
        field_name="responsible__username",
        to_field_name="username",
        queryset=lambda request: users_in_organization(request.user),
    )
    state = MultipleCharFilter(distinct=False)
    object_size = filters.RangeFilter()
    start_date = filters.IsoDateTimeFromToRangeFilter()
    end_date = filters.IsoDateTimeFromToRangeFilter()
    create_date = filters.IsoDateTimeFromToRangeFilter()
    entry_date = filters.IsoDateTimeFromToRangeFilter()
    package_type = MultipleCharFilter(distinct=False)
    package_type_name_exclude = filters.CharFilter(
        label=_("Excluded Package Type"),
        method='exclude_package_type_name'
    )
    migratable = filters.BooleanFilter(label='migratable', method='filter_migratable')
    exportable = filters.BooleanFilter(label='exportable', method='filter_exportable')
    workarea = filters.ChoiceFilter(label=_("Workarea"), field_name='workareas__type', choices=Workarea.TYPE_CHOICES)
    medium = filters.ModelMultipleChoiceFilter(
        label='Storage Medium', queryset=StorageMedium.objects.all(),
        field_name='storage__storage_medium',
        distinct=False
    )
    policy = filters.ModelChoiceFilter(
        label='Storage Policy', queryset=StoragePolicy.objects.all(),
        field_name='submission_agreement__policy',
        distinct=False
    )
    label = filters.CharFilter(field_name='label', lookup_expr='istartswith')

    def exclude_package_type_name(self, queryset, name, value):
        for package_type_id, package_type_name in InformationPackage.PACKAGE_TYPE_CHOICES:
            if package_type_name.lower() == value.lower():
                return queryset.exclude(package_type=package_type_id)
        return queryset.none()

    def filter_migratable(self, queryset, name, value):
        exportable = strtobool(self.data.get('exportable', False))
        export_path = 'dummy' if exportable else ''
        return queryset.migratable(export_path=export_path) if value else queryset

    def filter_exportable(self, queryset, name, value):
        return queryset.migratable(export_path='dummy') if value else queryset

    class Meta:
        model = InformationPackage
        fields = ['archivist_organization', 'state', 'responsible', 'active', 'label',
                  'create_date', 'entry_date', 'object_size', 'start_date', 'end_date', 'policy',
                  'archived', 'cached', 'package_type', 'package_type_name_exclude', 'workarea',
                  'object_identifier_value']


class EventIPFilter(filters.FilterSet):
    eventDateTime = filters.IsoDateTimeFromToRangeFilter()

    class Meta:
        model = EventIP
        fields = ('eventType', 'eventType__category', 'eventOutcome', 'linkingAgentRole', 'eventDateTime')


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


class WorkareaFilter(InformationPackageFilter):
    type = ListFilter(field_name='workareas__type', method='filter_workarea')

    def filter_workarea(self, queryset, name, value):
        workarea_type_reverse = dict((v.lower(), k) for k, v in Workarea.TYPE_CHOICES)

        try:
            workarea_type = workarea_type_reverse[value]
        except KeyError:
            raise exceptions.ParseError('Workarea of type "%s" does not exist' % value)

        return self.filterset_fields(queryset, name, workarea_type)

    class Meta:
        model = InformationPackage
        fields = InformationPackageFilter.Meta.fields + ['type']
