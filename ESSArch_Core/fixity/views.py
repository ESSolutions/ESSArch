from django.db.models import Exists, Max, Min, OuterRef
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework_extensions.mixins import NestedViewSetMixin

from .filters import ValidationFilter
from .models import Validation
from .serializers import ValidationFilesSerializer, ValidationSerializer


class ValidationViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Validation.objects.all().order_by('filename', 'validator')
    serializer_class = ValidationSerializer
    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend, filters.SearchFilter,
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
