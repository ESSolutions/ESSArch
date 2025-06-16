import elasticsearch
from django.db import transaction
from django.db.models import (
    CharField,
    Exists,
    OuterRef,
    ProtectedError,
    Q,
    Subquery,
)
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from mptt.templatetags.mptt_tags import cache_tree_children
from rest_framework import exceptions, filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.agents.models import AgentTagLink
from ESSArch_Core.api.filters import OrderingFilterWithNulls, SearchFilter
from ESSArch_Core.auth.decorators import permission_required_or_403
from ESSArch_Core.auth.permissions import ActionPermissions
from ESSArch_Core.configuration.decorators import feature_enabled_or_404
from ESSArch_Core.ip.views import InformationPackageViewSet
from ESSArch_Core.tags.documents import StructureUnitDocument
from ESSArch_Core.tags.filters import (
    StructureFilter,
    StructureUnitFilter,
    TagFilter,
)
from ESSArch_Core.tags.models import (
    Delivery,
    DeliveryType,
    Location,
    LocationFunctionType,
    LocationLevelType,
    MetricType,
    NodeIdentifierType,
    NodeNoteType,
    NodeRelationType,
    Search,
    Structure,
    StructureType,
    StructureUnit,
    StructureUnitType,
    Tag,
    TagVersion,
    TagVersionType,
    Transfer,
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
    LocationFunctionTypeSerializer,
    LocationLevelTypeSerializer,
    LocationSerializer,
    LocationWriteSerializer,
    MetricTypeSerializer,
    NodeIdentifierTypeSerializer,
    NodeNoteTypeSerializer,
    NodeRelationTypeSerializer,
    StoredSearchSerializer,
    StructureSerializer,
    StructureTypeSerializer,
    StructureUnitDetailSerializer,
    StructureUnitSerializer,
    StructureUnitTypeSerializer,
    StructureUnitWriteSerializer,
    StructureWriteSerializer,
    TagSerializer,
    TagVersionNestedSerializer,
    TagVersionTypeSerializer,
    TransferEditNodesSerializer,
    TransferSerializer,
)
from ESSArch_Core.util import mptt_to_dict
from ESSArch_Core.WorkflowEngine.models import ProcessTask


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class ArchiveViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = AgentTagLink.objects.filter(
        tag__elastic_index='archive'
    )
    permission_classes = (permissions.IsAuthenticated,)
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


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class MetricTypeViewSet(viewsets.ModelViewSet):
    queryset = MetricType.objects.all()
    serializer_class = MetricTypeSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class LocationLevelTypeViewSet(viewsets.ModelViewSet):
    queryset = LocationLevelType.objects.all()
    serializer_class = LocationLevelTypeSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class LocationFunctionTypeViewSet(viewsets.ModelViewSet):
    queryset = LocationFunctionType.objects.all()
    serializer_class = LocationFunctionTypeSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.none()
    serializer_class = LocationSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)

    def get_queryset(self):
        return Location.objects.for_user(self.request.user, [])

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return LocationWriteSerializer

        return self.serializer_class

    def list(self, request, *args, **kwargs):
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


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class NodeNoteTypeViewSet(viewsets.ModelViewSet):
    queryset = NodeNoteType.objects.all()
    serializer_class = NodeNoteTypeSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (DjangoFilterBackend, OrderingFilter, SearchFilter,)
    filterset_fields = ('history',)
    ordering_fields = ('name',)
    search_fields = ('name',)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class NodeIdentifierTypeViewSet(viewsets.ModelViewSet):
    queryset = NodeIdentifierType.objects.all()
    serializer_class = NodeIdentifierTypeSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class TagVersionViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = TagVersion.objects.all()
    serializer_class = TagVersionNestedSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)

    def get_queryset(self):
        return super().get_queryset().for_user(self.request.user, None).annotate(
            archive=Subquery(TagVersion.objects.filter(
                current_version_tags__structures__structure=OuterRef('tag__structures__structure'),
                type__archive_type=True,
            ).values('name')[:1], output_field=CharField())
        )


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class StructureTypeViewSet(viewsets.ModelViewSet):
    queryset = StructureType.objects.all()
    serializer_class = StructureTypeSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class StructureViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = Structure.objects.select_related('type').prefetch_related('units')
    serializer_class = StructureSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (DjangoFilterBackend, OrderingFilterWithNulls, SearchFilter,)
    filterset_class = StructureFilter
    ordering_fields = ('name', 'create_date', 'version', 'type', 'published_date',)
    search_fields = ('=id', 'name',)
    ordering = ('-create_date',)

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

        if obj.is_new_version():
            try:
                obj.is_compatible_with_last_version()
            except AssertionError:
                raise exceptions.ParseError(_('Structure is not compatible with latest publish version'))

        t = ProcessTask.objects.create(
            name='ESSArch_Core.tags.tasks.PublishStructure',
            params={
                'structure_id': obj.id
            },
            eager=False,
            responsible=request.user,
        )
        t.run()
        return Response({"detail": "Publish structure", "task": t.pk}, status=status.HTTP_202_ACCEPTED)

    @transaction.atomic
    @permission_required_or_403('tags.unpublish_structure')
    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        obj = self.get_object()

        if not obj.published:
            raise exceptions.ParseError(_('{} is not published').format(obj))

        obj.unpublish()
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

        qs = StructureUnit.objects.filter(structure=obj).select_related(
            'type__structure_type',
        ).prefetch_related(
            'identifiers',
            'notes',
            'structure__tagstructure_set',
            'structure_unit_relations_a',
        ).annotate(
            tag_leaf_node=~Exists(
                TagVersion.objects.for_user(request.user, None).filter(
                    tag__structures__structure=OuterRef('structure'),
                    tag__structures__structure_unit=OuterRef('pk'),
                ),
            )
        ).natural_sort()
        root_nodes = cache_tree_children(qs)
        dicts = []
        context = self.get_serializer_context()
        for n in root_nodes:
            dicts.append(mptt_to_dict(n, StructureUnitSerializer, context=context))

        return Response(dicts)

    @action(detail=True, methods=['get'])
    def instancestree(self, request, pk=None):
        obj = self.get_object()
        qs = obj.instances.all()
        root_nodes = qs
        context = self.get_serializer_context()

        return Response(StructureSerializer(root_nodes, many=True, context=context).data)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class StructureUnitTypeViewSet(viewsets.ModelViewSet):
    queryset = StructureUnitType.objects.all()
    serializer_class = StructureUnitTypeSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (DjangoFilterBackend, OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)
    filterset_fields = ('structure_type',)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class NodeRelationTypeViewSet(viewsets.ModelViewSet):
    queryset = NodeRelationType.objects.all()
    serializer_class = NodeRelationTypeSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (DjangoFilterBackend, OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class StructureUnitViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = StructureUnit.objects.none()
    serializer_class = StructureUnitSerializer
    permission_classes = (AddStructureUnit, ChangeStructureUnit, DeleteStructureUnit,)
    filter_backends = (DjangoFilterBackend, SearchFilter,)
    filterset_class = StructureUnitFilter
    search_fields = ('name',)

    def get_queryset(self):
        return self.filter_queryset_by_parents_lookups(
            StructureUnit.objects.for_user(self.request.user, perms=[])
        ).select_related(
            'structure', 'type__structure_type',
        ).prefetch_related(
            'identifiers', 'notes', 'structure_unit_relations_a',
        )

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return StructureUnitWriteSerializer

        if self.action == 'retrieve':
            return StructureUnitDetailSerializer

        return self.serializer_class

    def create(self, request, *args, **kwargs):
        parents_query_dict = self.get_parents_query_dict()
        if parents_query_dict:
            request.data.update(parents_query_dict)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        # Create elasticsearch document
        instance = serializer.instance
        doc = StructureUnitDocument.from_obj(instance)
        doc.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        parents_query_dict = self.get_parents_query_dict()
        if parents_query_dict:
            request.data.update(parents_query_dict)

        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Update elasticsearch document
        doc = StructureUnitDocument.from_obj(instance)
        doc.save()

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        with transaction.atomic():
            instance = self.get_object()
            structure = instance.structure

            if not structure.is_template and not structure.type.editable_instances:
                raise exceptions.ValidationError(
                    _('Cannot delete units in instances of type {}').format(structure.type)
                )
            # Delete elasticsearch document if exists
            try:
                doc = StructureUnitDocument.from_obj(instance)
                doc.get(doc.id)
            except elasticsearch.NotFoundError:
                pass
            else:
                instance.delete()
                doc.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            instance.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def nodes(self, request, pk=None, parent_lookup_structure=None):
        unit = self.get_object()

        structure = unit.structure
        if structure.tagstructure_set.exists():
            nodes = structure.tagstructure_set.first().get_root().tag.current_version.get_descendants(structure)
            children = nodes.filter(tag__structures__structure_unit=unit)
        else:
            children = TagVersion.objects.none()

        context = {'structure': structure, 'request': request, 'user': request.user, 'is_mixed_type': False}
        children = children.for_user(request.user).natural_sort()
        doument_index = False
        mixed_dict = {}
        for child in children:
            mixed_dict[child.type] = mixed_dict.get(child.type, 0) + 1
            if child.elastic_index == 'document':
                doument_index = True
        if len(mixed_dict) > 1 or doument_index:
            context['is_mixed_type'] = True

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

        children = unit.get_children().select_related(
            'structure', 'type__structure_type',
        ).prefetch_related(
            'identifiers', 'notes', 'structure_unit_relations_a',
        ).natural_sort()

        serializer = self.get_serializer_class()
        context = {
            'request': request,
            'user': request.user,
            'structure': request.query_params.get('structure')
        }
        if self.paginator is not None:
            paginated = self.paginator.paginate_queryset(children, request)
            serialized = serializer(instance=paginated, many=True, context=context).data
            return self.paginator.get_paginated_response(serialized)

        return Response(serializer(children, many=True, context=context).data)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class TagVersionTypeViewSet(viewsets.ModelViewSet):
    queryset = TagVersionType.objects.all()
    serializer_class = TagVersionTypeSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('archive_type',)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class TagViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = Tag.objects.none()
    serializer_class = TagSerializer

    filter_backends = (DjangoFilterBackend, SearchFilter)
    filterset_class = TagFilter
    search_fields = ('=current_version__id', 'current_version__name',)

    http_method_names = ('get', 'head', 'options')

    def get_queryset(self):
        user = self.request.user
        qs = Tag.objects.filter(current_version__in=TagVersion.objects.for_user(user, perms=[]))
        ancestor = self.kwargs.get('parent_lookup_tag')

        if ancestor is not None:
            ancestor = Tag.objects.get(pk=ancestor)
            structure = self.request.query_params.get('structure')
            qs = ancestor.get_descendants(structure)

        return qs


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class DeliveryViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = Delivery.objects.none()
    serializer_class = DeliverySerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (DjangoFilterBackend, SearchFilter, filters.OrderingFilter)
    filterset_fields = (
        'name', 'submission_agreement__name',
        'producer_organization__names__main',
    )
    search_fields = (
        '=id', 'name', 'description', 'submission_agreement__name',
        'producer_organization__names__main',
    )

    def get_queryset(self):
        user = self.request.user
        qs = Delivery.objects.for_user(user, [])
        return self.filter_queryset_by_parents_lookups(qs)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return DeliveryWriteSerializer

        return self.serializer_class


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class DeliveryTypeViewSet(viewsets.ModelViewSet):
    queryset = DeliveryType.objects.all()
    serializer_class = DeliveryTypeSerializer
    permission_classes = (ActionPermissions,)


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class TransferViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    queryset = Transfer.objects.none()
    serializer_class = TransferSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (SearchFilter, filters.OrderingFilter)
    filter_backends = (DjangoFilterBackend, SearchFilter, filters.OrderingFilter)
    filterset_fields = (
        'name', 'submitter_organization',
        'submitter_individual_name',
    )
    search_fields = (
        '=id', 'name', 'submitter_organization',
        'submitter_individual_name',
    )

    def get_queryset(self):
        user = self.request.user
        qs = Transfer.objects.for_user(user, [])
        return self.filter_queryset_by_parents_lookups(qs)

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

    @transaction.atomic
    @permission_required_or_403('tags.change_transfer')
    @action(detail=True, methods=['post'], url_path='add-nodes')
    def add_nodes(self, request, pk=None):
        transfer = self.get_object()

        serializer = TransferEditNodesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        transfer.structure_units.add(*data['structure_units'])
        transfer.tag_versions.add(*data['tags'])

        return Response()

    @transaction.atomic
    @permission_required_or_403('tags.change_transfer')
    @action(detail=True, methods=['post'], url_path='remove-nodes')
    def remove_nodes(self, request, pk=None):
        transfer = self.get_object()

        serializer = TransferEditNodesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        transfer.structure_units.remove(*data['structure_units'])
        transfer.tag_versions.remove(*data['tags'])

        return Response()


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class TagInformationPackagesViewSet(NestedViewSetMixin, InformationPackageViewSet):
    def filter_queryset_by_parents_lookups(self, queryset):
        parents_query_dict = self.get_parents_query_dict()
        tag = parents_query_dict['tag']
        leaves = Tag.objects.get(pk=tag).get_leafnodes(include_self=True)

        return queryset.filter(
            Q(tags__in=leaves) | Q(information_packages__tags__in=leaves) |
            Q(aic__information_packages__tags__in=leaves)
        )


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class StoredSearchViewSet(viewsets.ModelViewSet):
    queryset = Search.objects.all()
    serializer_class = StoredSearchSerializer

    filter_backends = (DjangoFilterBackend, SearchFilter)
    search_fields = ('name',)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)
