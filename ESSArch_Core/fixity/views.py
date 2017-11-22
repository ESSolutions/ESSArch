from rest_framework import viewsets

from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.serializers import ValidationSerializer


class ValidationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Validation.objects.all()
    serializer_class = ValidationSerializer
