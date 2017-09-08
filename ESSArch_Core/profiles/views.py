from rest_framework import exceptions

from ESSArch_Core.profiles.serializers import (
    ProfileIPSerializer,
    ProfileIPDataSerializer,
    ProfileIPWriteSerializer,
)

from ESSArch_Core.profiles.models import (
    ProfileIP, ProfileIPData,
)

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets


class ProfileIPViewSet(viewsets.ModelViewSet):
    queryset = ProfileIP.objects.all()

    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('ip', 'profile',)

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return ProfileIPSerializer

        return ProfileIPWriteSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.LockedBy is not None:
            detail = 'Method "{method}" is not allowed on locked profiles'.format(method=request.method)
            raise exceptions.MethodNotAllowed(method=request.method, detail=detail)

        return super(ProfileIPViewSet, self).update(request, *args, **kwargs)


class ProfileIPDataViewSet(viewsets.ModelViewSet):
    queryset = ProfileIPData.objects.all()
    serializer_class = ProfileIPDataSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.relation.LockedBy is not None:
            detail = 'Method "{method}" is not allowed on locked profiles'.format(method=request.method)
            raise exceptions.MethodNotAllowed(method=request.method, detail=detail)

        return super(ProfileIPDataViewSet, self).update(request, *args, **kwargs)
