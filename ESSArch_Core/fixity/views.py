from django.db.models import Exists, Max, Min, OuterRef
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, views, viewsets
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.api.filters import SearchFilter
from ESSArch_Core.fixity.filters import ValidationFilter
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.serializers import (
    ValidationFilesSerializer,
    ValidationSerializer,
    ValidatorWorkflowSerializer,
)
from ESSArch_Core.fixity.validation import (
    AVAILABLE_VALIDATORS,
    get_backend as get_validator,
)
from ESSArch_Core.WorkflowEngine.models import ProcessStep


class ValidatorViewSet(viewsets.ViewSet):
    permission_classes = ()

    def list(self, request, format=None):
        validators = {}
        for k, v in AVAILABLE_VALIDATORS.items():
            klass = get_validator(k)
            try:
                label = klass.label
            except AttributeError:
                label = klass.__name__

            try:
                form = klass.form()
            except AttributeError:
                form = {}

            validator = {
                'label': label,
                'form': form,
            }
            validators[k] = validator

        return Response(validators)


class ValidatorWorkflowViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = ProcessStep.objects.all()
    serializer_class = ValidatorWorkflowSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for validator in serializer.data['validators']:
            klass = get_validator(validator['name'])
            klass_serializer = klass.get_serializer_class()(data=validator['data'])
            klass_serializer.is_valid(raise_exception=True)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


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
