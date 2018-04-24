from django.db import transaction
from django.db.models import Max
from rest_framework_extensions.mixins import NestedViewSetMixin
from rest_framework import exceptions
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response

from ESSArch_Core.profiles.serializers import (
    ProfileIPSerializerWithData,
    ProfileIPSerializerWithProfileAndData,
    ProfileIPDataSerializer,
    ProfileIPDataTemplateSerializer,
    ProfileIPWriteSerializer,
)

from ESSArch_Core.profiles.models import (
    ProfileIP, ProfileIPData, ProfileIPDataTemplate
)

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets


class ProfileIPViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = ProfileIP.objects.all()

    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('ip', 'profile', 'profile__profile_type')

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return ProfileIPSerializerWithData

        return ProfileIPWriteSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.LockedBy is not None:
            detail = 'Method "{method}" is not allowed on locked profiles'.format(method=request.method)
            raise exceptions.MethodNotAllowed(method=request.method, detail=detail)

        return super(ProfileIPViewSet, self).update(request, *args, **kwargs)


class InformationPackageProfileIPViewSet(ProfileIPViewSet):
    queryset = ProfileIP.objects.all()
    http_method_names = ('get', 'head', 'options')

    def get_serializer_class(self):
        return ProfileIPSerializerWithProfileAndData


class ProfileIPDataViewSet(viewsets.ModelViewSet):
    queryset = ProfileIPData.objects.all()
    serializer_class = ProfileIPDataSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.relation.LockedBy is not None:
            detail = 'Method "{method}" is not allowed on locked profiles'.format(method=request.method)
            raise exceptions.MethodNotAllowed(method=request.method, detail=detail)

        return super(ProfileIPDataViewSet, self).update(request, *args, **kwargs)

    @transaction.atomic
    @list_route(methods=['post'], url_path='import-from-template')
    def import_from_template(self, request):
        relation = request.data.get('relation')
        relation = ProfileIP.objects.get(pk=relation)
        template = request.data.get('template')
        template = ProfileIPDataTemplate.objects.get(pk=template, profile=relation.profile)
        max_version = relation.data_versions.aggregate(Max('version'))['version__max']
        profile_ip_obj = ProfileIPData.objects.create(relation=relation, data=template.data, user=request.user,
                                                      version=max_version + 1)
        return Response(ProfileIPDataSerializer(profile_ip_obj).data)

    @detail_route(methods=['post'], url_path='save-as-template')
    def save_as_template(self, request, pk=None):
        obj = self.get_object()
        name = request.data.get('name')
        if not name:
            raise exceptions.ParseError('Missing "name" parameter')

        template, _ = ProfileIPDataTemplate.objects.update_or_create(name=name, profile=obj.relation.profile,
                                                                     defaults={'data': obj.data})
        return Response(ProfileIPDataTemplateSerializer(template).data)


class ProfileIPDataTemplateViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'head', 'options']
    queryset = ProfileIPDataTemplate.objects.all()
    serializer_class = ProfileIPDataTemplateSerializer
