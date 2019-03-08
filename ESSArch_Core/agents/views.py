from django.db.models import F, Prefetch
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from ESSArch_Core.agents.models import (
    Agent,
    AgentIdentifier,
    AgentName,
    AgentNote,
    AgentPlace,
    AgentRelation,
    SourcesOfAuthority,
)
from ESSArch_Core.agents.serializers import (
    AgentSerializer,
    AgentWriteSerializer,
)


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.select_related(
        'type__main_type', 'ref_code', 'language',
    ).prefetch_related(
        Prefetch('names', AgentName.objects.prefetch_related('type')),
        Prefetch('identifiers', AgentIdentifier.objects.prefetch_related('type').order_by('type__name', 'identifier')),
        Prefetch('agentplace_set', AgentPlace.objects.prefetch_related('topography', 'type',).order_by(F('start_date').desc(nulls_first=True))),
        Prefetch('notes', AgentNote.objects.prefetch_related('type').order_by('-create_date')),
        Prefetch('mandates', SourcesOfAuthority.objects.prefetch_related('type').order_by(F('start_date').desc(nulls_first=True))),
        Prefetch('agent_relations_a', AgentRelation.objects.prefetch_related('agent_b').order_by(F('start_date').desc(nulls_first=True))),
    )
    serializer_class = AgentSerializer
    filter_backends = (OrderingFilter, SearchFilter,)
    ordering_fields = ('names__part', 'names__main', 'start_date', 'end_date',)
    search_fields = ('names__part', 'names__main',)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return AgentWriteSerializer

        return self.serializer_class
