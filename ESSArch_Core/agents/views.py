from django.db.models import F, Prefetch
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ESSArch_Core.agents.filters import AgentFilter, AgentOrderingFilter
from ESSArch_Core.agents.models import (
    Agent,
    AgentIdentifier,
    AgentIdentifierType,
    AgentName,
    AgentNameType,
    AgentNote,
    AgentNoteType,
    AgentPlace,
    AgentPlaceType,
    AgentRelation,
    AgentRelationType,
    AgentTagLinkRelationType,
    AgentType,
    AuthorityType,
    RefCode,
    SourcesOfAuthority,
)
from ESSArch_Core.agents.serializers import (
    AgentIdentifierTypeSerializer,
    AgentNameTypeSerializer,
    AgentNoteTypeSerializer,
    AgentPlaceTypeSerializer,
    AgentRelationTypeSerializer,
    AgentSerializer,
    AgentTagLinkRelationTypeSerializer,
    AgentTypeSerializer,
    AgentWriteSerializer,
    AuthorityTypeSerializer,
    RefCodeSerializer,
)
from ESSArch_Core.api.filters import SearchFilter
from ESSArch_Core.auth.permissions import ActionPermissions
from ESSArch_Core.auth.serializers import ChangeOrganizationSerializer
from ESSArch_Core.configuration.decorators import feature_enabled_or_404


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class AgentRelationTypeViewSet(viewsets.ModelViewSet):
    queryset = AgentRelationType.objects.all()
    serializer_class = AgentRelationTypeSerializer
    permission_classes = (ActionPermissions,)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class AgentTagLinkRelationTypeViewSet(viewsets.ModelViewSet):
    queryset = AgentTagLinkRelationType.objects.all()
    serializer_class = AgentTagLinkRelationTypeSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('creator',)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class AgentTypeViewSet(viewsets.ModelViewSet):
    queryset = AgentType.objects.select_related('main_type')
    serializer_class = AgentTypeSerializer
    permission_classes = (ActionPermissions,)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class AgentNameTypeViewSet(viewsets.ModelViewSet):
    queryset = AgentNameType.objects.all()
    serializer_class = AgentNameTypeSerializer
    permission_classes = (ActionPermissions,)

    filter_backends = (DjangoFilterBackend, SearchFilter,)
    filterset_fields = ('authority',)
    search_fields = ('name',)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class AgentNoteTypeViewSet(viewsets.ModelViewSet):
    queryset = AgentNoteType.objects.all()
    serializer_class = AgentNoteTypeSerializer
    permission_classes = (ActionPermissions,)

    filter_backends = (DjangoFilterBackend, SearchFilter,)
    filterset_fields = ('history',)
    search_fields = ('name',)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class AgentIdentifierTypeViewSet(viewsets.ModelViewSet):
    queryset = AgentIdentifierType.objects.all()
    serializer_class = AgentIdentifierTypeSerializer
    permission_classes = (ActionPermissions,)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class AgentPlaceTypeViewSet(viewsets.ModelViewSet):
    queryset = AgentPlaceType.objects.all()
    serializer_class = AgentPlaceTypeSerializer
    permission_classes = (ActionPermissions,)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.none()
    serializer_class = AgentSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (AgentOrderingFilter, DjangoFilterBackend, SearchFilter,)
    filterset_class = AgentFilter
    ordering_fields = ('latest_name', 'names__part', 'names__main', 'start_date', 'end_date', 'type__main_type__name')
    search_fields = ('=id', 'names__part', 'names__main')
    ordering = ('-create_date',)

    def get_queryset(self):
        user = self.request.user

        return Agent.objects.for_user(user, []).select_related(
            'type__main_type', 'ref_code', 'language',
        ).prefetch_related(
            Prefetch('names', AgentName.objects.prefetch_related('type')),
            Prefetch(
                'identifiers',
                AgentIdentifier.objects.prefetch_related('type').order_by('type__name', 'identifier')
            ),
            Prefetch(
                'agentplace_set',
                AgentPlace.objects.prefetch_related(
                    'topography', 'type',
                ).order_by(F('start_date').desc(nulls_first=True))
            ),
            Prefetch('notes', AgentNote.objects.prefetch_related('type').order_by('-create_date')),
            Prefetch(
                'mandates',
                SourcesOfAuthority.objects.prefetch_related('type').order_by(F('start_date').desc(nulls_first=True))
            ),
            Prefetch(
                'agent_relations_a',
                AgentRelation.objects.prefetch_related('agent_b').order_by(F('start_date').desc(nulls_first=True))
            ),
        )

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return AgentWriteSerializer

        return self.serializer_class

    @action(detail=True, methods=['post'], url_path='change-organization')
    def change_organization(self, request, pk=None):
        agent = self.get_object()

        serializer = ChangeOrganizationSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        organization = serializer.validated_data['organization']
        force = serializer.validated_data['force']
        change_related_Archives = serializer.validated_data['change_related_Archives']
        change_related_Archives_force = serializer.validated_data['change_related_Archives_force']
        change_related_StructureUnits = serializer.validated_data['change_related_StructureUnits']
        change_related_StructureUnits_force = serializer.validated_data['change_related_StructureUnits_force']
        change_related_Nodes = serializer.validated_data['change_related_Nodes']
        change_related_Nodes_force = serializer.validated_data['change_related_Nodes_force']
        change_related_IPs = serializer.validated_data['change_related_IPs']
        change_related_IPs_force = serializer.validated_data['change_related_IPs_force']
        change_related_AIDs = serializer.validated_data['change_related_AIDs']
        change_related_AIDs_force = serializer.validated_data['change_related_AIDs_force']

        agent.change_organization(organization, force=force,
                                  change_related_Archives=change_related_Archives,
                                  change_related_Archives_force=change_related_Archives_force,
                                  change_related_StructureUnits=change_related_StructureUnits,
                                  change_related_StructureUnits_force=change_related_StructureUnits_force,
                                  change_related_Nodes=change_related_Nodes,
                                  change_related_Nodes_force=change_related_Nodes_force,
                                  change_related_IPs=change_related_IPs,
                                  change_related_IPs_force=change_related_IPs_force,
                                  change_related_AIDs=change_related_AIDs,
                                  change_related_AIDs_force=change_related_AIDs_force)
        return Response()


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class AuthorityTypeViewSet(viewsets.ModelViewSet):
    queryset = AuthorityType.objects.all()
    serializer_class = AuthorityTypeSerializer
    permission_classes = (ActionPermissions,)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class RefCodeViewSet(viewsets.ModelViewSet):
    queryset = RefCode.objects.all()
    serializer_class = RefCodeSerializer
    permission_classes = (ActionPermissions,)
