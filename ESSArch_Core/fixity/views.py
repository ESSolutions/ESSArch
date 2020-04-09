from django.db.models import Exists, Max, Min, OuterRef
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.api.filters import SearchFilter
from ESSArch_Core.fixity.filters import ValidationFilter
from ESSArch_Core.fixity.models import ConversionTool, Validation
from ESSArch_Core.fixity.serializers import (
    ConversionToolSerializer,
    ValidationFilesSerializer,
    ValidationSerializer,
)
from ESSArch_Core.fixity.validation import (
    AVAILABLE_VALIDATORS,
    get_backend as get_validator,
)


class ConversionToolViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = ConversionTool.objects.filter(enabled=True)
    serializer_class = ConversionToolSerializer


class ValidatorViewSet(viewsets.ViewSet):
    permission_classes = ()

    def list(self, request, format=None):
        validators = {}
        for k, _ in AVAILABLE_VALIDATORS.items():
            klass = get_validator(k)
            try:
                label = klass.label
            except AttributeError:
                label = klass.__name__

            try:
                form = klass.get_form()
            except AttributeError:
                form = []

            validator = {
                'label': label,
                'form': form,
            }
            validators[k] = validator

        return Response(validators)


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
