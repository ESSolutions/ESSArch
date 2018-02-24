from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import exceptions, filters, status, viewsets
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from rest_framework_extensions.mixins import NestedViewSetMixin

import six

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.fixity.validation import AVAILABLE_VALIDATORS
from ESSArch_Core.ip.filters import (
    ArchivalInstitutionFilter,
    ArchivistOrganizationFilter,
    ArchivalTypeFilter,
    ArchivalLocationFilter,
    EventIPFilter,
)
from ESSArch_Core.ip.models import (
    ArchivalInstitution,
    ArchivistOrganization,
    ArchivalType,
    ArchivalLocation,
    EventIP,
    InformationPackage,
    Workarea,
)
from ESSArch_Core.ip.serializers import (
    ArchivalInstitutionSerializer,
    ArchivistOrganizationSerializer,
    ArchivalTypeSerializer,
    ArchivalLocationSerializer,
    EventIPSerializer,
    WorkareaSerializer,
)
from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask
from ESSArch_Core.util import remove_prefix


class ArchivalInstitutionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows archival institutions to be viewed or edited.
    """
    queryset = ArchivalInstitution.objects.all()
    serializer_class = ArchivalInstitutionSerializer

    filter_backends = (DjangoFilterBackend,)
    filter_class = ArchivalInstitutionFilter


class ArchivistOrganizationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows archivist organizations to be viewed or edited.
    """
    queryset = ArchivistOrganization.objects.all()
    serializer_class = ArchivistOrganizationSerializer

    filter_backends = (DjangoFilterBackend,)
    filter_class = ArchivistOrganizationFilter


class ArchivalTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows archival types to be viewed or edited.
    """
    queryset = ArchivalType.objects.all()
    serializer_class = ArchivalTypeSerializer

    filter_backends = (DjangoFilterBackend,)
    filter_class = ArchivalTypeFilter


class ArchivalLocationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows archival locations to be viewed or edited.
    """
    queryset = ArchivalLocation.objects.all()
    serializer_class = ArchivalLocationSerializer

    filter_backends = (DjangoFilterBackend,)
    filter_class = ArchivalLocationFilter

class EventIPViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows events to be viewed or edited.
    """
    queryset = EventIP.objects.all()
    serializer_class = EventIPSerializer
    filter_class = EventIPFilter
    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend, filters.SearchFilter,
    )
    ordering_fields = (
        'id', 'eventType', 'eventOutcomeDetailNote', 'eventOutcome',
        'linkingAgentIdentifierValue', 'eventDateTime',
    )
    search_fields = ('eventOutcomeDetailNote',)


class WorkareaEntryViewSet(viewsets.ModelViewSet):
    queryset = Workarea.objects.all()
    serializer_class = WorkareaSerializer

    def get_queryset(self):
        see_all = self.request.user.has_perm('ip.see_all_in_workspaces')
        ips = InformationPackage.objects.visible_to_user(self.request.user)

        qs = self.queryset.filter(ip__in=ips)
        if not see_all:
            qs = qs.filter(user=self.request.user)

        return qs

    @detail_route(methods=['post'], url_path='validate')
    def validate(self, request, pk=None):
        workarea = self.get_object()
        ip = workarea.ip
        task_name = "ESSArch_Core.tasks.ValidateWorkarea"

        if ip.get_profile('validation') is None:
            raise exceptions.ParseError("IP does not have a \"validation\" profile")

        if ProcessTask.objects.filter(information_package=ip, name=task_name, time_done__isnull=True).exists():
            raise exceptions.ParseError('"{objid}" is already being validated'.format(objid=ip.object_identifier_value))

        ip.validation_set.all().delete()

        stop_at_failure = request.data.get('stop_at_failure', False)
        validators = request.data.get('validators', {})
        available_validators = AVAILABLE_VALIDATORS.keys()

        if not any(selected in available_validators for selected in validators):
            raise exceptions.ParseError('No valid validator selected')

        for selected in validators:
            if selected not in available_validators:
                raise exceptions.ParseError('Validator "%s" not found' % selected)
            if selected not in ip.get_profile('validation').specification.keys():
                raise exceptions.ParseError('Validator "%s" not specified in validation profile' % selected)

        params = {'validators': validators, 'stop_at_failure': stop_at_failure}

        task = ProcessTask.objects.create(
            name=task_name,
            args=[pk],
            params=params,
            eager=False,
            log=EventIP,
            information_package=ip,
            responsible=self.request.user,
        )
        task.run()
        return Response("Validating IP")

    @detail_route(methods=['post'], url_path='transform')
    def transform(self, request, pk=None):
        workarea = self.get_object()
        ip = workarea.ip

        if ip.state.lower() in ('transforming', 'transformed'):
            raise exceptions.ParseError("\"{ip}\" already {state}".format(ip=ip.object_identifier_value, state=ip.state.lower()))

        if ip.get_profile('transformation') is None:
            raise exceptions.ParseError("IP does not have a \"transformation\" profile")

        if ip.get_profile('validation') is not None:
            for validator, successful in six.iteritems(workarea.successfully_validated):
                if successful is not True:
                    raise exceptions.ParseError("\"{ip}\" hasn't been successfully validated with \"{validator}\"".format(ip=ip.object_identifier_value, validator=validator))

        step = ProcessStep.objects.create(name="Transform", eager=False, information_package=ip)
        pos = 0

        ProcessTask.objects.create(
            name="ESSArch_Core.tasks.UpdateIPStatus",
            params={
                "ip": ip.pk,
                "status": "Transforming",
                "prev": ip.state,
            },
            processstep=step,
            processstep_pos=pos,
            log=EventIP,
            information_package=ip,
            responsible=request.user,
        )

        pos += 10

        ProcessTask.objects.create(
            name="ESSArch_Core.tasks.TransformWorkarea",
            args=[pk],
            log=EventIP,
            processstep=step,
            processstep_pos=pos,
            information_package=ip,
            responsible=request.user,
        )

        pos += 10

        ProcessTask.objects.create(
            name="ESSArch_Core.tasks.UpdateIPStatus",
            params={
                "ip": ip.pk,
                "status": "Transformed",
                "prev": "Transforming",
            },
            processstep=step,
            processstep_pos=pos,
            log=EventIP,
            information_package=ip,
            responsible=request.user,
        )
        step.run()

        return Response("Transforming IP")

    def destroy(self, request, pk=None, **kwargs):
        workarea = self.get_object()

        if not workarea.read_only:
            workarea.ip.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return super(WorkareaEntryViewSet, self).destroy(request, pk, **kwargs)
