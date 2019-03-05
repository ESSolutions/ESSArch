from django.db.models import Prefetch
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from ESSArch_Core.tags.models import (
    Agent,
    AgentIdentifier,
    AgentName,
    AgentNote,
    AgentPlace,
    AgentRelation,
    SourcesOfAuthority,
)
from ESSArch_Core.tags.serializers import (
    AgentSerializer,
    AgentWriteSerializer,
)


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.select_related(
        'type__main_type', 'ref_code', 'language',
    ).prefetch_related(
        Prefetch('names', AgentName.objects.prefetch_related('type')),
        Prefetch('identifiers', AgentIdentifier.objects.prefetch_related('type')),
        Prefetch('agentplace_set', AgentPlace.objects.prefetch_related('topography', 'type',)),
        Prefetch('notes', AgentNote.objects.prefetch_related('type')),
        Prefetch('mandates', SourcesOfAuthority.objects.prefetch_related('type')),
        Prefetch('agent_relations_a', AgentRelation.objects.prefetch_related('agent_b')),
    )
    serializer_class = AgentSerializer
    filter_backends = (OrderingFilter, SearchFilter,)
    ordering_fields = ('names__part', 'names__main', 'start_date', 'end_date',)
    search_fields = ('names__part', 'names__main',)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return AgentWriteSerializer

        return self.serializer_class
