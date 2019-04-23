from django.db import transaction
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
from ESSArch_Core.api.filters import OrderingFilterWithNulls
from ESSArch_Core.tags.filters import StructureUnitFilter, TagFilter
from ESSArch_Core.tags.models import (
    Structure,
    StructureType,
    StructureUnit,
    StructureUnitType,
    Tag,
    TagVersionType
)
from ESSArch_Core.tags.permissions import (
    AddStructureUnit,
    ChangeStructureUnit,
)
from ESSArch_Core.tags.serializers import (
    AgentArchiveLinkSerializer,
    AgentArchiveLinkWriteSerializer,
    TagSerializer,
    TagVersionNestedSerializer,
    TagVersionTypeSerializer,
    StructureSerializer,
    StructureTypeSerializer,
    StructureWriteSerializer,
    StructureUnitSerializer,
    StructureUnitTypeSerializer,
    StructureUnitWriteSerializer,
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


class StructureUnitViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = StructureUnit.objects.select_related('structure')
    serializer_class = StructureUnitSerializer
    permission_classes = (ActionPermissions, AddStructureUnit, ChangeStructureUnit,)
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
