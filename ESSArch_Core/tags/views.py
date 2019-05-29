from django.db import transaction
from django.db.models import Q, ProtectedError
from django.utils.translation import ugettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from mptt.templatetags.mptt_tags import cache_tree_children
from rest_framework import exceptions, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.agents.models import AgentTagLink
from ESSArch_Core.auth.decorators import permission_required_or_403
from ESSArch_Core.auth.permissions import ActionPermissions
from ESSArch_Core.auth.util import get_objects_for_user
from ESSArch_Core.api.filters import OrderingFilterWithNulls
from ESSArch_Core.ip.models import EventIP
from ESSArch_Core.ip.serializers import EventIPSerializer
from ESSArch_Core.tags.filters import StructureUnitFilter, TagFilter
from ESSArch_Core.tags.models import (
    Delivery,
    DeliveryType,
    Structure,
    StructureType,
    StructureUnit,
    StructureUnitType,
    NodeRelationType,
    Tag,
    TagVersion,
    TagVersionType,
    Transfer,
    Location,
    MetricProfile,
    LocationLevelType,
    LocationFunctionType,
)
from ESSArch_Core.tags.permissions import (
    AddStructureUnit,
    ChangeStructureUnit,
    DeleteStructureUnit,
)
from ESSArch_Core.tags.serializers import (
    AgentArchiveLinkSerializer,
    AgentArchiveLinkWriteSerializer,
    DeliverySerializer,
    DeliveryTypeSerializer,
    DeliveryWriteSerializer,
    TagSerializer,
    TagVersionNestedSerializer,
    TagVersionTypeSerializer,
    StructureSerializer,
    StructureTypeSerializer,
    StructureWriteSerializer,
    StructureUnitSerializer,
    StructureUnitTypeSerializer,
    NodeRelationTypeSerializer,
    StructureUnitWriteSerializer,
    LocationSerializer,
    MetricProfileSerializer,
    LocationLevelTypeSerializer,
    LocationFunctionTypeSerializer,
    LocationWriteSerializer,
    TransferEditNodesSerializer,
    TransferSerializer,
)
from ESSArch_Core.util import mptt_to_dict


class ArchiveViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = AgentTagLink.objects.filter(
        tag__elastic_index='archive'
    )
    serializer_class = AgentArchiveLinkSerializer
    filter_backends = (OrderingFilter, SearchFilter,)
    search_fields = ('tag__name',)
    ordering_fields = ('tag__name',)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return AgentArchiveLinkWriteSerializer

        return self.serializer_class

    def create(self, request, *args, **kwargs):
        parents_query_dict = self.get_parents_query_dict()
        if parents_query_dict:
            request.data.update(parents_query_dict)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        parents_query_dict = self.get_parents_query_dict()
        if parents_query_dict:
            request.data.update(parents_query_dict)
        return super().update(request, *args, **kwargs)


class MetricProfileViewSet(viewsets.ModelViewSet):
    queryset = MetricProfile.objects.all()
    serializer_class = MetricProfileSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)


class LocationLevelTypeViewSet(viewsets.ModelViewSet):
    queryset = LocationLevelType.objects.all()
    serializer_class = LocationLevelTypeSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)


class LocationFunctionTypeViewSet(viewsets.ModelViewSet):
    queryset = LocationFunctionType.objects.all()
    serializer_class = LocationFunctionTypeSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)

    def get_queryset(self):
        return get_objects_for_user(self.request.user, Location, [])

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return LocationWriteSerializer

        return self.serializer_class

    def list(self, request):
        qs = self.filter_queryset(self.get_queryset())
        root_nodes = cache_tree_children(qs)
        dicts = []
        for n in root_nodes:
            dicts.append(mptt_to_dict(n, LocationSerializer))

        return Response(dicts)

    def destroy(self, request, *args, **kwargs):
        try:
            resp = super().destroy(request, *args, **kwargs)
        except ProtectedError:
            raise exceptions.ParseError(_('Location must be empty before deletion'))
        else:
            return resp

class TagVersionViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = TagVersion.objects.all()
    serializer_class = TagVersionNestedSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)


class StructureTypeViewSet(viewsets.ModelViewSet):
    queryset = StructureType.objects.all()
    serializer_class = StructureTypeSerializer
    permission_classes = (DjangoModelPermissions,)
    filter_backends = (OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)


class StructureViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = Structure.objects.select_related('type').prefetch_related('units')
    serializer_class = StructureSerializer
    permission_classes = (DjangoModelPermissions,)
    filter_backends = (DjangoFilterBackend, OrderingFilterWithNulls, SearchFilter,)
    filterset_fields = ('type', 'is_template', 'published',)
    ordering_fields = ('name', 'create_date', 'version', 'type', 'published_date',)
    search_fields = ('name',)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return StructureWriteSerializer

        return self.serializer_class

    @transaction.atomic
    @permission_required_or_403('tags.publish_structure')
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        obj = self.get_object()

        if not obj.is_template:
            raise exceptions.ParseError(_('Can only publish templates'))

        if obj.published:
            raise exceptions.ParseError(_('{} is already published').format(obj))

        obj.publish()
        return Response()

    @transaction.atomic
    @permission_required_or_403('tags.create_new_structure_version')
    @action(detail=True, methods=['post'], url_path='new-version')
    def new_version(self, request, pk=None):
        obj = self.get_object()

        if not obj.is_template:
            raise exceptions.ParseError(_('Can only create new versions of templates'))

        if not obj.published:
            raise exceptions.ParseError(_('Can only create new versions of published structures'))

        try:
            version_name = request.data['version_name']
        except KeyError:
            raise exceptions.ParseError(_('No version name provided'))

        if Structure.objects.filter(is_template=True, version_link=obj.version_link, version=version_name).exists():
            raise exceptions.ParseError(_('Version {} already exists').format(version_name))

        new_version = obj.create_new_version(version_name)
        serializer = self.serializer_class(instance=new_version)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def tree(self, request, pk=None):
        obj = self.get_object()

        qs = StructureUnit.objects.filter(structure=obj)
        root_nodes = cache_tree_children(qs)
        dicts = []
        for n in root_nodes:
            dicts.append(mptt_to_dict(n, StructureUnitSerializer))

        return Response(dicts)


class StructureUnitTypeViewSet(viewsets.ModelViewSet):
    queryset = StructureUnitType.objects.all()
    serializer_class = StructureUnitTypeSerializer
    permission_classes = (DjangoModelPermissions,)
    filter_backends = (DjangoFilterBackend, OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)
    filterset_fields = ('structure_type',)


class NodeRelationTypeViewSet(viewsets.ModelViewSet):
    queryset = NodeRelationType.objects.all()
    serializer_class = NodeRelationTypeSerializer
    permission_classes = (DjangoModelPermissions,)
    filter_backends = (DjangoFilterBackend, OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)


class StructureUnitViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = StructureUnit.objects.select_related('structure')
    serializer_class = StructureUnitSerializer
    permission_classes = (ActionPermissions, AddStructureUnit, ChangeStructureUnit, DeleteStructureUnit,)
    filter_backends = (DjangoFilterBackend, SearchFilter,)
    filter_class = StructureUnitFilter
    search_fields = ('name',)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return StructureUnitWriteSerializer

        return self.serializer_class

    def create(self, request, *args, **kwargs):
        parents_query_dict = self.get_parents_query_dict()
        if parents_query_dict:
            request.data.update(parents_query_dict)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        parents_query_dict = self.get_parents_query_dict()
        if parents_query_dict:
            request.data.update(parents_query_dict)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        structure = instance.structure

        if not structure.is_template and not structure.type.editable_instances:
            raise exceptions.ValidationError(
                _('Cannot delete units in instances of type {}').format(structure.type)
            )

        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def nodes(self, request, pk=None, parent_lookup_structure=None):
        unit = self.get_object()

        structure = unit.structure
        nodes = structure.tagstructure_set.first().get_root().tag.current_version.get_descendants(structure)
        children = nodes.filter(tag__structures__structure_unit=unit)

        context = {'structure': structure, 'user': request.user}

        if self.paginator is not None:
            paginated = self.paginator.paginate_queryset(children, request)
            serialized = TagVersionNestedSerializer(instance=paginated, many=True, context=context).data
            return self.paginator.get_paginated_response(serialized)

        return Response(TagVersionNestedSerializer(children, many=True, context=context).data)

    @action(detail=True, methods=['get'])
    def children(self, request, pk=None, parent_lookup_structure=None):
        unit = self.get_object()
        if unit.is_leaf_node():
            return self.nodes(request, pk, parent_lookup_structure)

        children = unit.get_children()
        serializer = self.get_serializer_class()
        context = {
            'user': request.user,
            'structure': request.query_params.get('structure')
        }
        if self.paginator is not None:
            paginated = self.paginator.paginate_queryset(children, request)
            serialized = serializer(instance=paginated, many=True, context=context).data
            return self.paginator.get_paginated_response(serialized)

        return Response(serializer(children, many=True, context=context).data)


class TagVersionTypeViewSet(viewsets.ModelViewSet):
    queryset = TagVersionType.objects.all()
    serializer_class = TagVersionTypeSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('archive_type',)


class TagViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

    filter_backends = (DjangoFilterBackend, SearchFilter)
    filterset_class = TagFilter
    search_fields = ('current_version__name',)

    http_method_names = ('get', 'head', 'options')

    def get_queryset(self):
        qs = self.queryset
        ancestor = self.kwargs.get('parent_lookup_tag')

        if ancestor is not None:
            ancestor = Tag.objects.get(pk=ancestor)
            structure = self.request.query_params.get('structure')
            qs = ancestor.get_descendants(structure)

        return qs


class DeliveryViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer
    permission_classes = (ActionPermissions,)

    @action(detail=True, methods=['GET'], url_path='events')
    def events(self, request, pk):
        delivery = self.get_object()
        qs = EventIP.objects.filter(Q(delivery=delivery) | Q(transfer__delivery=delivery))
        page = self.paginate_queryset(qs)
        if page is not None:
            serializers = EventIPSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializers.data)
        serializers = EventIPSerializer(qs, many=True, context={'request': request})
        return Response(serializers.data)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return DeliveryWriteSerializer

        return self.serializer_class


class DeliveryTypeViewSet(viewsets.ModelViewSet):
    queryset = DeliveryType.objects.all()
    serializer_class = DeliveryTypeSerializer
    permission_classes = (ActionPermissions,)


class TransferViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer
    permission_classes = (ActionPermissions,)

    def create(self, request, *args, **kwargs):
        # https://github.com/chibisov/drf-extensions/issues/142

        parents_query_dict = self.get_parents_query_dict()
        if parents_query_dict:
            request.data.update(parents_query_dict)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        # https://github.com/chibisov/drf-extensions/issues/142

        parents_query_dict = self.get_parents_query_dict()
        if parents_query_dict:
            request.data.update(parents_query_dict)
        return super().update(request, *args, **kwargs)

    @transaction.atomic()
    @action(detail=True, methods=['post'], url_path='add-nodes')
    def add_nodes(self, request, pk=None):
        transfer = self.get_object()

        serializer = TransferEditNodesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        transfer.structure_units.add(*data['structure_units'])
        transfer.tag_versions.add(*data['tags'])

        return Response()

    @transaction.atomic()
    @action(detail=True, methods=['post'], url_path='remove-nodes')
    def remove_nodes(self, request, pk=None):
        transfer = self.get_object()

        serializer = TransferEditNodesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        transfer.structure_units.remove(*data['structure_units'])
        transfer.tag_versions.remove(*data['tags'])

        return Response()
