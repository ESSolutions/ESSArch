from django.db import transaction
from django.db.models import Max, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_extensions.mixins import NestedViewSetMixin
from rest_framework import exceptions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import DjangoModelPermissions, SAFE_METHODS

from ESSArch_Core.profiles.models import (
    Profile,
    ProfileIP,
    ProfileIPData,
    ProfileIPDataTemplate,
    SubmissionAgreement,
    ProfileSA,
)
from ESSArch_Core.profiles.serializers import ProfileSASerializer, SubmissionAgreementSerializer
from ESSArch_Core.profiles.serializers import (
    ProfileSerializer,
    ProfileDetailSerializer,
    ProfileWriteSerializer,
    ProfileIPSerializerWithData,
    ProfileIPSerializerWithProfileAndData,
    ProfileIPDataSerializer,
    ProfileIPDataTemplateSerializer,
    ProfileIPWriteSerializer,
    ProfileSASerializer,
    SubmissionAgreementSerializer,
)


class SubmissionAgreementViewSet(viewsets.ModelViewSet):
    queryset = SubmissionAgreement.objects.all().prefetch_related(
        Prefetch('profilesa_set', to_attr='profiles')
    )
    serializer_class = SubmissionAgreementSerializer
    permission_classes = (DjangoModelPermissions,)
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('published',)

    @action(detail=True)
    def profiles(self, request, pk=None):
        sa = self.get_object()
        profiles = [p for p in sa.get_profiles() if p is not None]
        return Response(ProfileSerializer([p for p in profiles if p is not None], many=True).data)


class ProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows profiles to be viewed or edited.
    """
    queryset = Profile.objects.all()
    permission_classes = (DjangoModelPermissions,)

    def get_serializer_class(self):
        if self.action == 'list':
            return ProfileSerializer

        if self.action == 'retrieve':
            return ProfileDetailSerializer

        return ProfileWriteSerializer

    def get_queryset(self):
        queryset = Profile.objects.all()
        profile_type = self.request.query_params.get('type', None)

        if profile_type is not None:
            queryset = queryset.filter(profile_type=profile_type)

        return queryset


class ProfileIPViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = ProfileIP.objects.all()

    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('ip', 'profile', 'profile__profile_type')

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return ProfileIPSerializerWithData

        return ProfileIPWriteSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.LockedBy is not None:
            detail = 'Method "{method}" is not allowed on locked profiles'.format(method=request.method)
            raise exceptions.MethodNotAllowed(method=request.method, detail=detail)

        return super().update(request, *args, **kwargs)


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

        return super().update(request, *args, **kwargs)

    @transaction.atomic
    @action(detail=False, methods=['post'], url_path='import-from-template')
    def import_from_template(self, request):
        relation = request.data.get('relation')
        relation = ProfileIP.objects.get(pk=relation)
        template = request.data.get('template')
        template = ProfileIPDataTemplate.objects.get(pk=template, profile=relation.profile)
        max_version = relation.data_versions.aggregate(Max('version'))['version__max']
        profile_ip_obj = ProfileIPData.objects.create(relation=relation, data=template.data, user=request.user,
                                                      version=max_version + 1)
        return Response(ProfileIPDataSerializer(profile_ip_obj).data)

    @action(detail=True, methods=['post'], url_path='save-as-template')
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


class ProfileSAViewSet(viewsets.ModelViewSet):
    queryset = ProfileSA.objects.all()
    serializer_class = ProfileSASerializer
