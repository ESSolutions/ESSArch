from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from mptt.templatetags.mptt_tags import cache_tree_children
from rest_framework import exceptions, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.auth.permissions import ActionPermissions
from ESSArch_Core.ip.views import InformationPackageViewSet
from ESSArch_Core.tags.filters import StructureUnitFilter, TagFilter
from ESSArch_Core.tags.models import Structure, StructureUnit, Tag, TagVersion
from ESSArch_Core.tags.serializers import (
    StructureSerializer,
    StructureUnitSerializer,
    TagSerializer,
    TagVersionNestedSerializer,
)
from ESSArch_Core.util import mptt_to_dict


class StructureViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = Structure.objects.prefetch_related('units')
    serializer_class = StructureSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (OrderingFilter, SearchFilter,)
    ordering_fields = ('name', 'create_date', 'version',)
    search_fields = ('name',)

    @action(detail=True, methods=['get'])
    def tree(self, request, pk=None):
        obj = self.get_object()

        qs = StructureUnit.objects.filter(structure=obj)
        root_nodes = cache_tree_children(qs)
        dicts = []
        for n in root_nodes:
            dicts.append(mptt_to_dict(n, StructureUnitSerializer))

        return Response(dicts)


class StructureUnitViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = StructureUnit.objects.select_related('structure')
    serializer_class = StructureUnitSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = StructureUnitFilter

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['archive'] = self.request.query_params.get('archive')
        return context

    def perform_create(self, serializer):
        try:
            structure = self.get_parents_query_dict()['structure']
        except KeyError:
            structure = self.get_parents_query_dict()['parent__structure']
        parent = serializer.validated_data.get('parent')
        if parent is not None and str(parent.structure.pk) != structure:
            raise exceptions.ValidationError('Parent must be from the same classification structure')
        serializer.save(structure_id=structure)

    @action(detail=True, methods=['get'])
    def nodes(self, request, pk=None, parent_lookup_structure=None):
        archive_id = request.query_params.get('archive')
        unit = self.get_object()

        structure = unit.structure
        try:
            nodes = TagVersion.objects.get(pk=archive_id).get_descendants(structure)
        except TagVersion.DoesNotExist:
            raise exceptions.ParseError('Invalid archive {}'.format(archive_id))
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
            'archive': request.query_params.get('archive'),
            'structure': request.query_params.get('structure')
        }
        if self.paginator is not None:
            paginated = self.paginator.paginate_queryset(children, request)
            serialized = serializer(instance=paginated, many=True, context=context).data
            return self.paginator.get_paginated_response(serialized)

        return Response(serializer(children, many=True, context=context).data)


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


class TagInformationPackagesViewSet(NestedViewSetMixin, InformationPackageViewSet):
    def filter_queryset_by_parents_lookups(self, queryset):
        parents_query_dict = self.get_parents_query_dict()
        tag = parents_query_dict['tag']
        leaves = Tag.objects.get(pk=tag).get_leafnodes(include_self=True)

        return queryset.filter(
            Q(tags__in=leaves) | Q(information_packages__tags__in=leaves) |
            Q(aic__information_packages__tags__in=leaves)
        ).distinct()
