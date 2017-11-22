from rest_framework import viewsets

from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.serializers import ValidationSerializer


class ValidationViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Validation.objects.all().order_by('filename', 'validator')
    serializer_class = ValidationSerializer
