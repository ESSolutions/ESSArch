from django.db.models import Exists, Max, Min, OuterRef
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.api.filters import SearchFilter
from ESSArch_Core.fixity.filters import ValidationFilter
from ESSArch_Core.fixity.models import ActionTool, Validation
from ESSArch_Core.fixity.serializers import (
    SaveActionToolSerializer,
    ActionToolSerializer,
    ValidationFilesSerializer,
    ValidationSerializer,
)


class ActionToolViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = ActionTool.objects.filter(enabled=True)
    serializer_class = ActionToolSerializer

class SaveActionToolViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = ActionTool.objects.filter(enabled=True)
    serializer_class = SaveActionToolSerializer

class ValidationViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Validation.objects.all().order_by('filename', 'validator')
    serializer_class = ValidationSerializer
    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend, SearchFilter,
    )
    filterset_class = ValidationFilter
    search_fields = ('filename', 'message',)


class ValidationFilesViewSet(ValidationViewSet):
    sub = Validation.objects.filter(
        information_package=OuterRef('information_package'),
        filename=OuterRef('filename'), passed=False, required=True,
    )

    queryset = Validation.objects.distinct().values('filename').annotate(
        time_started=Min('time_started'), time_done=Max('time_done'),
        passed=~Exists(sub),
    ).order_by('time_started')

    serializer_class = ValidationFilesSerializer
