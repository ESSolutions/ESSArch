from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import exceptions, filters, status, viewsets
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.configuration.models import Path
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
from ESSArch_Core.WorkflowEngine.models import ProcessTask
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
        return self.queryset.filter(user=self.request.user)

    @detail_route(methods=['post'], url_path='validate')
    def validate(self, request, pk=None):
        workarea = self.get_object()
        ip = workarea.ip
        ip.validation_set.all().delete()

        prepare = Path.objects.get(entity="ingest_workarea").value

        stop_at_failure = request.data.get('stop_at_failure', False)
        validators = request.data.get('validators', {})
        available_validators = [
            'validate_xml_file', 'validate_file_format', 'validate_integrity',
            'validate_logical_physical_representation', 'validate_mediaconch',
        ]

        if not any(v is True and k in available_validators for k, v in validators.iteritems()):
            raise exceptions.ParseError('No valid validator selected')

        for key in validators:
            if validators[key]:
                validators[remove_prefix(key, 'validate_')] = validators.pop(key)

        params = {'stop_at_failure': stop_at_failure}
        params.update(validators)

        task = ProcessTask.objects.create(
            name="ESSArch_Core.tasks.ValidateWorkarea",
            args=[pk],
            params=params,
            eager=False,
            log=EventIP,
            information_package=ip,
            responsible=self.request.user,
        )
        task.run()
        return Response("Validating IP")

    def destroy(self, request, pk=None, **kwargs):
        workarea = self.get_object()

        if not workarea.read_only:
            workarea.ip.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return super(WorkareaEntryViewSet, self).destroy(request, pk, **kwargs)
