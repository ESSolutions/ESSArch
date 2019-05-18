from django.db import transaction
from django.db.models import Max, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_extensions.mixins import NestedViewSetMixin
from rest_framework import exceptions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import DjangoModelPermissions, SAFE_METHODS

from ESSArch_Core.ip.models import Agent, InformationPackage
from ESSArch_Core.ip.permissions import CanLockSA
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

    @action(detail=True, methods=['post'], url_path='include-type')
    def include_type(self, request, pk=None):
        sa = SubmissionAgreement.objects.get(pk=pk)
        ptype = request.data["type"]

        setattr(sa, "include_profile_%s" % ptype, True)
        sa.save()

        return Response({
            'status': 'Including profile type %s in SA %s' % (ptype, sa)
        })

    @action(detail=True, methods=['post'], url_path='exclude-type')
    def exclude_type(self, request, pk=None):
        sa = SubmissionAgreement.objects.get(pk=pk)
        ptype = request.data["type"]

        setattr(sa, "include_profile_%s" % ptype, False)
        sa.save()

        return Response({
            'status': 'Excluding profile type %s in SA %s' % (ptype, sa)
        })

    @action(detail=True, methods=['post'])
    def save(self, request, pk=None):
        if not request.user.has_perm('profiles.create_new_sa_generation'):
            raise exceptions.PermissionDenied

        sa = self.get_object()

        try:
            new_name = request.data["new_name"]
        except KeyError:
            new_name = ''

        if not new_name:
            return Response(
                {'status': 'No name specified'},
                status=status.HTTP_400_BAD_REQUEST
            )

        new_data = request.data.get("data", {})

        changed_data = False

        for field in sa.template:
            if field.get('templateOptions', {}).get('required', False):
                if not new_data.get(field['key'], None):
                    return Response(
                        {"status': 'missing required field '%s'" % field['key']},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        for k, v in new_data.items():
            if v != getattr(sa, k):
                changed_data = True
                break

        if not changed_data:
            return Response({'status': 'no changes, not saving'}, status=status.HTTP_400_BAD_REQUEST)

        new_sa = sa.copy(new_data=new_data, new_name=new_name,)
        serializer = SubmissionAgreementSerializer(
            new_sa, context={'request': request}
        )
        return Response(serializer.data)

    def get_profile_types(self):
        return 'sip', 'transfer_project', 'submit_description', 'preservation_metadata'

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        sa = self.get_object()
        ip_id = request.data.get("ip")
        permission = CanLockSA()

        try:
            ip = InformationPackage.objects.get(pk=ip_id)
        except InformationPackage.DoesNotExist:
            raise exceptions.ParseError('Information Package with id %s does not exist')

        if ip.submission_agreement_locked:
            raise exceptions.ParseError('IP already has a locked SA')

        if not permission.has_object_permission(request, self, ip):
            self.permission_denied(request, message=getattr(permission, 'message', None))

        if ip.submission_agreement != sa:
            raise exceptions.ParseError('This SA is not connected to the selected IP')

        ip.submission_agreement_locked = True
        if sa.archivist_organization:
            existing_agents_with_notes = Agent.objects.all().with_notes([])
            ao_agent, _ = Agent.objects.get_or_create(
                role='ARCHIVIST', type='ORGANIZATION',
                name=sa.archivist_organization, pk__in=existing_agents_with_notes
            )
            ip.agents.add(ao_agent)
        ip.save()

        ip.create_profile_rels(self.get_profile_types(), request.user)
        return Response({'status': 'Locked submission agreement'})


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
