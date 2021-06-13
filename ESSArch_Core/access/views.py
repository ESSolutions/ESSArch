from django.db.models import F, Prefetch
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response


from ESSArch_Core.access.models import (
    AccessAid,
    AccessAidType
)
from ESSArch_Core.access.serializers import (
    AccessAidSerializer,
    AccessAidTypeSerializer,
    AccessAidWriteSerializer

)
from ESSArch_Core.api.filters import SearchFilter
from ESSArch_Core.auth.permissions import ActionPermissions
from ESSArch_Core.auth.serializers import ChangeOrganizationSerializer
from ESSArch_Core.configuration.decorators import feature_enabled_or_404


class AccessAidTypeViewSet(viewsets.ModelViewSet):
    queryset = AccessAidType.objects.all()
    serializer_class = AccessAidTypeSerializer
    permission_classes = (ActionPermissions,)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return AccessAidTypeSerializer

        return self.serializer_class


class AccessAidViewSet(viewsets.ModelViewSet):
    queryset = AccessAid.objects.none()
    serializer_class = AccessAidSerializer
    permission_classes = (ActionPermissions,)

    def get_queryset(self):
        user = self.request.user


        return AccessAid.objects.for_user(user, []).all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return AccessAidWriteSerializer

        return self.serializer_class




