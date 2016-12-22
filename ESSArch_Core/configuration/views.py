from ESSArch_Core.configuration.models import (
    Agent,
    EventType,
    Parameter,
    Path,
)

from ESSArch_Core.configuration.serializers import(
    AgentSerializer,
    EventTypeSerializer,
    ParameterSerializer,
    PathSerializer,
)

from rest_framework import viewsets


class EventTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows event types to be viewed or edited.
    """
    queryset = EventType.objects.all()
    serializer_class = EventTypeSerializer
    pagination_class = None


class AgentViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows agents to be viewed or edited.
    """
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer


class ParameterViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows parameters to be viewed or edited.
    """
    queryset = Parameter.objects.all()
    serializer_class = ParameterSerializer


class PathViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows paths to be viewed or edited.
    """
    queryset = Path.objects.all()
    serializer_class = PathSerializer
