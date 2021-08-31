from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.access.models import AccessAid, AccessAidType
from ESSArch_Core.access.serializers import (
    AccessAidEditNodesSerializer,
    AccessAidSerializer,
    AccessAidTypeSerializer,
    AccessAidWriteSerializer,
)
from ESSArch_Core.api.filters import SearchFilter
from ESSArch_Core.auth.decorators import permission_required_or_403
from ESSArch_Core.auth.permissions import ActionPermissions


class AccessAidTypeViewSet(viewsets.ModelViewSet):
    queryset = AccessAidType.objects.all()
    serializer_class = AccessAidTypeSerializer
    permission_classes = (ActionPermissions,)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return AccessAidTypeSerializer

        return self.serializer_class


class AccessAidViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = AccessAid.objects.none()
    serializer_class = AccessAidSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (filters.OrderingFilter, DjangoFilterBackend, SearchFilter,)
    ordering_fields = ('name', 'type', 'security_level', 'start_date', 'end_date')
    search_fields = ('=id', 'name')

    def get_queryset(self):
        user = self.request.user
        qs = AccessAid.objects.for_user(user, [])
        return self.filter_queryset_by_parents_lookups(qs)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return AccessAidWriteSerializer

        return self.serializer_class

    @transaction.atomic
    @permission_required_or_403('access.change_accessaid')
    @action(detail=True, methods=['post'], url_path='add-nodes')
    def add_structure_unit(self, request, pk=None):
        access_aid = self.get_object()
        serializer = AccessAidEditNodesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        access_aid.structure_units.add(*data['structure_units'])
        return Response()

    @transaction.atomic
    @permission_required_or_403('access.change_accessaid')
    @action(detail=True, methods=['post'], url_path='remove-nodes')
    def remove_structure_unit(self, request, pk=None):
        access_aid = self.get_object()
        serializer = AccessAidEditNodesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        access_aid.structure_units.remove(*data['structure_units'])
        return Response()
