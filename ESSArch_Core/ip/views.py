from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters, viewsets

from ESSArch_Core.ip.models import EventIP
from ESSArch_Core.ip.serializers import EventIPSerializer


class EventIPViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows events to be viewed or edited.
    """
    queryset = EventIP.objects.all()
    serializer_class = EventIPSerializer
    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend,
    )
    ordering_fields = (
        'id', 'eventType', 'eventOutcomeDetailNote', 'eventOutcome',
        'linkingAgentIdentifierValue', 'eventDateTime',
    )
