from django.db.models import QuerySet, Min, Max, Case, Value, When, NullBooleanField, Subquery, OuterRef, CharField

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters, viewsets
from rest_framework.decorators import list_route
from rest_framework.response import Response

from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.serializers import ValidationSerializer, ValidationFilesSerializer


class ValidationViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Validation.objects.all().order_by('filename', 'validator')
    serializer_class = ValidationSerializer
    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend, filters.SearchFilter,
    )
    filter_fields = ('filename', 'validator', 'passed', 'information_package',)


class ValidationFilesViewSet(ValidationViewSet):
    sub = Validation.objects.filter(
        information_package=OuterRef('information_package'),
        filename=OuterRef('filename')
    ).order_by('passed')

    queryset = Validation.objects.distinct().values('filename').annotate(
        time_started=Min('time_started'), time_done=Max('time_done'),
        passed=Subquery(sub.values('passed')[:1]),
    ).order_by('time_started')

    serializer_class = ValidationFilesSerializer
