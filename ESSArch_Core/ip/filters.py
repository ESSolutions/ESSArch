from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from django_filters import rest_framework as filters
from rest_framework import exceptions

from ESSArch_Core.api.filters import ListFilter, MultipleCharFilter
from ESSArch_Core.ip.models import Agent, EventIP, InformationPackage, Workarea

User = get_user_model()


def users(request):
    org = request.user.user_profile.current_organization
    if org is None:
        if request.user.is_superuser:
            return User.objects.all()
        return User.objects.filter(pk=request.user.pk)
    return User.objects.filter(essauth_member__in=org.members)


def states():
    result = InformationPackage.objects.order_by().values_list('state', flat=True).distinct()
    return [(state, state.capitalize()) for state in result]


class AgentFilter(filters.FilterSet):
    ip_state = ListFilter(field_name='information_packages__state', distinct=True)

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
        queryset=users
    )
    state = MultipleCharFilter()
    object_size = filters.RangeFilter()
    start_date = filters.IsoDateTimeFromToRangeFilter()
    end_date = filters.IsoDateTimeFromToRangeFilter()
    create_date = filters.IsoDateTimeFromToRangeFilter()
    entry_date = filters.IsoDateTimeFromToRangeFilter()
    package_type = MultipleCharFilter()
    package_type_name_exclude = filters.CharFilter(
        label=_("Excluded Package Type"),
        method='exclude_package_type_name'
    )

    def exclude_package_type_name(self, queryset, name, value):
        for package_type_id, package_type_name in InformationPackage.PACKAGE_TYPE_CHOICES:
            if package_type_name.lower() == value.lower():
                return queryset.exclude(package_type=package_type_id)
        return queryset.none()

    class Meta:
        model = InformationPackage
        fields = ['archivist_organization', 'state', 'responsible',
                  'create_date', 'entry_date', 'object_size', 'start_date', 'end_date',
                  'archived', 'cached', 'package_type', 'package_type_name_exclude']


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
