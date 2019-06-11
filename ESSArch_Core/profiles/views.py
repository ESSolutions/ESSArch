import copy
import json
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import exceptions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.essxml.ProfileMaker.models import (
    extensionPackage,
    templatePackage,
)
from ESSArch_Core.essxml.ProfileMaker.views import (
    calculateChildrenBefore,
    generateElement,
    removeChildren,
)
from ESSArch_Core.ip.models import Agent, InformationPackage
from ESSArch_Core.ip.permissions import CanLockSA
from ESSArch_Core.profiles.models import (
    Profile,
    ProfileIP,
    ProfileIPData,
    ProfileIPDataTemplate,
    ProfileSA,
    SubmissionAgreement,
)
from ESSArch_Core.profiles.serializers import (
    ProfileDetailSerializer,
    ProfileIPDataSerializer,
    ProfileIPDataTemplateSerializer,
    ProfileIPSerializerWithData,
    ProfileIPSerializerWithProfileAndData,
    ProfileIPWriteSerializer,
    ProfileMakerExtensionSerializer,
    ProfileMakerTemplateSerializer,
    ProfileSASerializer,
    ProfileSerializer,
    ProfileWriteSerializer,
    SubmissionAgreementSerializer,
)


def get_sa_template():
    path = os.path.join(settings.BASE_DIR, 'templates/SUBMISSION_AGREEMENT.json')
    with open(path) as json_file:
        return json.load(json_file)


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

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        if SubmissionAgreement.objects.values_list('published', flat=True).get(pk=pk):
            raise exceptions.ParseError('Submission agreement is already published')

        template = get_sa_template()
        SubmissionAgreement.objects.filter(pk=pk).update(published=True, template=template)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.published:
            detail = 'Method "{method}" is not allowed on published SAs'.format(method=request.method)
            raise exceptions.MethodNotAllowed(method=request.method, detail=detail)

        return super().update(request, *args, **kwargs)

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

    @action(detail=True, methods=['post'])
    def save(self, request, pk=None):
        profile = Profile.objects.get(pk=pk)
        new_data = request.data.get("specification_data", {})
        new_structure = request.data.get("structure", {})

        changed_data = (profile.specification_data.keys().sort() == new_data.keys().sort() and
                        profile.specification_data != new_data)

        changed_structure = profile.structure != new_structure

        if (changed_data or changed_structure):
            try:
                new_profile = profile.copy(
                    specification_data=new_data,
                    new_name=request.data["new_name"],
                    structure=new_structure,
                )
            except ValidationError as e:
                raise exceptions.ParseError(e)

            serializer = ProfileSerializer(
                new_profile, context={'request': request}
            )
            return Response(serializer.data)

        return Response({'status': 'no changes, not saving'}, status=status.HTTP_400_BAD_REQUEST)


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


class ProfileMakerExtensionViewSet(viewsets.ModelViewSet):
    queryset = extensionPackage.objects.all()
    serializer_class = ProfileMakerExtensionSerializer


class ProfileMakerTemplateViewSet(viewsets.ModelViewSet):
    queryset = templatePackage.objects.all()
    serializer_class = ProfileMakerTemplateSerializer

    @action(detail=True, methods=['post'], url_path='add-child')
    def add_child(self, request, pk=None):
        required = ['name', 'parent']

        # validate input
        missing_items = {
            field_name: 'This field is required'
            for field_name in required
            if field_name not in request.data
        }
        if missing_items:
            raise exceptions.ValidationError(missing_items, code='required')

        obj = self.get_object()

        existingElements = obj.existingElements
        templates = obj.allElements

        new_name = request.data['name']
        parent = request.data['parent']
        new_uuid = str(uuid.uuid4())

        if parent not in existingElements:
            raise exceptions.ValidationError({'parent': '"%s" not in the tree' % parent})

        newElement = None

        # ensure that the element exists in any of the schemas
        if new_name in templates:
            newElement = copy.deepcopy(templates[new_name])
        else:
            for extension in obj.extensions.all():
                if new_name in extension.allElements:
                    newElement = copy.deepcopy(extension.allElements[new_name])

        if newElement is None:
            raise exceptions.ValidationError({'name': '"%s" not in any of the schemas' % new_name})

        newElement['parent'] = parent
        existingElements[new_uuid] = newElement

        # If there are multiple of the same element under the same parent
        # then we need to know the position of the last element with
        # the same name

        try:
            child_list = [c['name'] for c in existingElements[parent]['children']]
            index = len(child_list) - list(reversed(child_list)).index(new_name)
        except ValueError:
            index = 0

        # calculate which elements should be before the new element
        cb = calculateChildrenBefore(existingElements[parent]['availableChildren'], new_name)

        if index == 0:
            for child in existingElements[parent]['children']:
                if child['name'] not in cb:
                    break
                else:
                    index += 1

        e = {
            'name': new_name,
            'uuid': new_uuid
        }
        existingElements[parent]['children'].insert(index, e)
        obj.save()
        return Response(existingElements, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='delete-element')
    def delete_element(self, request, pk=None):
        required = ['uuid']

        # validate input
        missing_items = {
            field_name: 'This field is required'
            for field_name in required
            if field_name not in request.data
        }
        if missing_items:
            raise exceptions.ValidationError(missing_items, code='required')

        obj = self.get_object()
        el_uuid = request.data['uuid']

        try:
            el = obj.existingElements[el_uuid]
        except KeyError:
            raise exceptions.ValidationError({'uuid': 'Invalid uuid "%s" - element does not exist' % el_uuid})

        parent = obj.existingElements[el['parent']]

        # delete element in list of children of parent
        parent['children'][:] = [c for c in parent['children'] if c.get('uuid') != el_uuid]

        # delete the children of the element
        removeChildren(obj.existingElements, el)

        # delete the element
        del obj.existingElements[el_uuid]

        obj.save(update_fields=['existingElements'])
        return Response(obj.existingElements, status=status.HTTP_200_OK)

    @action(detail=True, methods=['put'], url_path='update-element')
    def update_element(self, request, pk=None):
        required = ['uuid', 'data']

        # validate input
        missing_items = {
            field_name: 'This field is required'
            for field_name in required
            if field_name not in request.data
        }
        if missing_items:
            raise exceptions.ValidationError(missing_items, code='required')

        obj = self.get_object()
        el_uuid = request.data['uuid']
        data = request.data['data']

        try:
            obj.existingElements[el_uuid]
        except KeyError:
            raise exceptions.ValidationError({'uuid': 'Invalid uuid "%s" - element does not exist' % el_uuid})

        obj.existingElements[el_uuid]['formData'] = data

        obj.save(update_fields=['existingElements'])
        return Response(obj.existingElements, status=status.HTTP_200_OK)

    @action(detail=True, methods=['put'], url_path='update-contains-files')
    def update_contains_files(self, request, pk=None):
        required = ['uuid', 'contains_files']

        # validate input
        missing_items = {
            field_name: 'This field is required'
            for field_name in required
            if field_name not in request.data
        }
        if missing_items:
            raise exceptions.ValidationError(missing_items, code='required')

        obj = self.get_object()
        el_uuid = request.data['uuid']
        val = request.data['contains_files']

        try:
            obj.existingElements[el_uuid]
        except KeyError:
            raise exceptions.ValidationError({'uuid': 'Invalid uuid "%s" - element does not exist' % el_uuid})

        if type(val) is not bool:
            raise exceptions.ValidationError({'contains_files': 'Must be a boolean'})

        obj.existingElements[el_uuid]['containsFiles'] = val
        obj.save(update_fields=['existingElements'])
        return Response(obj.existingElements, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='add-attribute')
    def add_attribute(self, request, pk=None):
        required = ['uuid', 'data']

        # validate input
        missing_items = {
            field_name: 'This field is required'
            for field_name in required
            if field_name not in request.data
        }
        if missing_items:
            raise exceptions.ValidationError(missing_items, code='required')

        obj = self.get_object()
        el_uuid = request.data['uuid']
        data = request.data['data']

        try:
            obj.existingElements[el_uuid]
        except KeyError:
            raise exceptions.ValidationError({'uuid': 'Invalid uuid "%s" - element does not exist' % el_uuid})

        obj.existingElements[el_uuid]['userForm'].append(data)
        obj.save(update_fields=['existingElements'])
        return Response(obj.existingElements, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        class SimpleProfileSerializer(serializers.ModelSerializer):
            class Meta:
                model = Profile
                fields = (
                    'id', 'profile_type', 'name', 'type', 'status', 'label',
                )

        def addExtraAttribute(field, data, attr):
            """
            Adds extra attribute to field if it exists in data
            Args:
                field: The field to add to
                data: The data dictionary to look in
                attr: The name of the attribute to add
            Returns:
                The new field with the attribute added to it if the attribute
                exists in data. Otherwise the original field.
            """

            field_attr = field['key'] + '_' + attr

            if field_attr in data:
                field[attr] = data[field_attr]

            return field

        serializer = SimpleProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        obj = self.get_object()
        existingElements = obj.existingElements

        form = existingElements['root']['form']
        formData = existingElements['root']['formData']

        for idx, field in enumerate(form):
            field = addExtraAttribute(field, formData, 'desc')
            field = addExtraAttribute(field, formData, 'hideExpression')
            field = addExtraAttribute(field, formData, 'readonly')

            form[idx] = field

        existingElements['root']['form'] = form

        nsmap = obj.nsmap

        for ext in obj.extensions.iterator():
            nsmap.update(ext.nsmap)

        schemaLocation = ['%s %s' % (obj.targetNamespace, obj.schemaURL)]

        XSI = 'http://www.w3.org/2001/XMLSchema-instance'

        if not nsmap.get("xsi"):
            nsmap["xsi"] = XSI

        if not nsmap.get(obj.prefix):
            nsmap[obj.prefix] = obj.targetNamespace

        for ext in obj.extensions.all():
            nsmap[ext.prefix] = ext.targetNamespace
            schemaLocation.append('%s %s' % (ext.targetNamespace, ext.schemaURL))

        jsonString, forms, data = generateElement(existingElements, 'root', nsmap=nsmap)

        schemaLocation = ({
            '-name': 'schemaLocation',
            '-namespace': 'xsi',
            '#content': [{
                'text': ' '.join(schemaLocation)
            }]
        })

        jsonString['-attr'].append(schemaLocation)

        profile = Profile.objects.create(
            profile_type=validated_data['profile_type'],
            name=validated_data['name'], type=validated_data['type'],
            status=validated_data['status'], label=validated_data['label'],
            template=forms, specification=jsonString, specification_data=data,
            structure=obj.structure
        )

        profile_data = ProfileSerializer(profile, context={'request': request}).data

        return Response(profile_data, status=status.HTTP_201_CREATED)


class SubmissionAgreementTemplateView(APIView):
    def get(self, request):
        return Response(get_sa_template())
