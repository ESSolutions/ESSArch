from django.db.models import QuerySet, Min, Max, Case, Value, When, NullBooleanField, Exists, OuterRef, CharField

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters, viewsets
from rest_framework.decorators import list_route
from rest_framework.response import Response

from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.fixity.filters import ValidationFilter
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.serializers import ValidationSerializer, ValidationFilesSerializer


class ValidationViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Validation.objects.all().order_by('filename', 'validator')
    serializer_class = ValidationSerializer
    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend, filters.SearchFilter,
    )
    filter_class = ValidationFilter


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
