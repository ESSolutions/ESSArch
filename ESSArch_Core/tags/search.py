import copy
import csv
import datetime
import io
import json
import logging
import math
import os
import tempfile

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Prefetch
from django.template.loader import render_to_string
from django.utils import timezone
from django_filters.constants import EMPTY_VALUES
from elasticsearch.exceptions import NotFoundError, TransportError
from elasticsearch_dsl import FacetedSearch, Q, TermsFacet
from elasticsearch_dsl.connections import get_connection
from rest_framework import exceptions, serializers, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from weasyprint import HTML

from ESSArch_Core.agents.models import AgentTagLink
from ESSArch_Core.auth.models import GroupGenericObjects
from ESSArch_Core.auth.serializers import ChangeOrganizationSerializer
from ESSArch_Core.auth.util import get_objects_for_user
from ESSArch_Core.mixins import PaginatedViewMixin
from ESSArch_Core.search import DEFAULT_MAX_RESULT_WINDOW
from ESSArch_Core.tags.documents import Archive, VersionedDocType
from ESSArch_Core.tags.models import Structure, TagStructure, TagVersion
from ESSArch_Core.tags.permissions import SearchPermissions
from ESSArch_Core.tags.serializers import (
    ArchiveWriteSerializer,
    ComponentWriteSerializer,
    TagVersionNestedSerializer,
    TagVersionSerializerWithVersions,
    TagVersionWriteSerializer,
)
from ESSArch_Core.util import generate_file_response, remove_prefix

logger = logging.getLogger('essarch.search')
EXPORT_FORMATS = ('csv', 'pdf')
SORTABLE_FIELDS = (
    {'name.keyword': {'unmapped_type': 'keyword'}},
    {'reference_code.keyword': {'unmapped_type': 'keyword'}}
)


class ComponentSearch(FacetedSearch):
    index = ['component', 'archive', 'document', 'information_package', 'structure_unit']
    fields = [
        'reference_code.keyword^5', 'reference_code^3', 'name^2', 'desc', 'attachment.content',
        'attachment.keywords',
    ]

    facets = {
        # use bucket aggregations to define facets
        'extension': TermsFacet(field='extension', min_doc_count=0, size=100),
        'type': TermsFacet(field='type', min_doc_count=0, size=100),
    }

    filters = {
        'agents': {'many': True},
        'extensions': {'many': True},
        'start_date': {},
        'end_date': {},
        'type': {'many': True},
    }

    def __init__(self, *args, **kwargs):
        self.query_params_filter = kwargs.pop('filter_values', {})
        self.start_date = self.query_params_filter.pop('start_date', None)
        self.end_date = self.query_params_filter.pop('end_date', None)
        self.archives = self.query_params_filter.pop('archives', None)
        self.personal_identification_number = self.query_params_filter.pop('personal_identification_number', None)
        self.user = kwargs.pop('user')
        self.filter_values = {
            'indices': self.query_params_filter.pop('indices', [])
        }

        def validate_date(d):
            try:
                return datetime.datetime.strptime(d, '%Y')
            except ValueError:
                try:
                    return datetime.datetime.strptime(d, '%Y-%m')
                except ValueError:
                    try:
                        return datetime.datetime.strptime(d, '%Y-%m-%d')
                    except ValueError:
                        raise exceptions.ParseError('Invalid date format, should be YYYY[-MM-DD]')

        if self.start_date not in EMPTY_VALUES:
            self.start_date = self.start_date.zfill(4)
            self.start_date = validate_date(self.start_date)

        if self.end_date not in EMPTY_VALUES:
            self.end_date = self.end_date.zfill(4)
            self.end_date = validate_date(self.end_date)

        if self.start_date not in EMPTY_VALUES and self.end_date not in EMPTY_VALUES:
            if self.start_date > self.end_date:
                raise exceptions.ParseError('start_date cannot be set to date after end_date')

        super().__init__(*args, **kwargs)

    def search(self):
        """
        We override this to add filters on archive, start and end date

        We have to manually filter archives since we want to filter against a
        script field representing the archive which is the `archive` field on
        components and `_id` on archives.
        """

        organization_archives = get_objects_for_user(self.user, TagVersion.objects.filter(elastic_index='archive'), [])
        organization_archives = [str(x) for x in list(organization_archives.values_list('pk', flat=True))]

        s = super().search()
        s = s.source(excludes=["attachment.content"])

        # only get current version of "TagVersion" documents
        s = s.query('bool', minimum_should_match=1, should=[
            Q('term', current_version=True),
            Q('bool', must_not=Q('terms', index=[
                'archive-*',
                'component-*'
            ])),
        ])

        s = s.filter(Q('bool', minimum_should_match=1, should=[
            Q('bool', **{'must_not': {'exists': {'field': 'archive'}}}),
            Q('nested', path='archive', ignore_unmapped=True, query=Q('terms', archive__id=organization_archives)),
            Q('bool', minimum_should_match=1, should=[
                Q('bool', must=[
                    Q('bool', must_not=Q('term', _index='archive-*')),
                    Q('nested', path='archive', ignore_unmapped=True, query=Q(
                        'bool', **{'must_not': {'exists': {'field': 'archive'}}}
                    )),
                ]),
                Q('bool', must=[
                    Q('term', _index='archive-*'),
                    Q('terms', _id=organization_archives)
                ])
            ]),
        ]))

        s = s.query('bool', minimum_should_match=1, should=[
            Q('term', current_version=True),
            Q('bool', must_not=Q('terms', index=[
                'archive-*',
                'component-*'
            ])),
        ])

        if self.personal_identification_number not in EMPTY_VALUES:
            s = s.filter('term', personal_identification_numbers=self.personal_identification_number)

        if self.start_date not in EMPTY_VALUES:
            s = s.filter('range', end_date={'gte': self.start_date})

        if self.end_date not in EMPTY_VALUES:
            s = s.filter('range', start_date={'lte': self.end_date})

        if self.archives is not None:
            s = s.filter(Q('bool', minimum_should_match=1, should=[
                Q('nested', path='archive', ignore_unmapped=True, query=Q(
                    'terms', archive__id=self.archives.split(',')
                )),
                Q('bool', must=[
                    Q('bool', must_not=Q('exists', field='archive')),
                    Q('terms', _id=self.archives.split(',')),
                ])
            ]))

        for filter_k, filter_v in self.query_params_filter.items():
            if filter_k in self.filters and filter_v not in EMPTY_VALUES:
                if self.filters[filter_k].get('many', False):
                    filter_v = filter_v.split(',')
                    s = s.query('terms', **{filter_k: filter_v})

                else:
                    s = s.query('match', **{filter_k: filter_v})

        return s

    def highlight(self, search):
        """
        We override this to set the highlighting options
        """

        pre_tags = ["<strong>"]
        post_tags = ["</strong>"]
        search = search.highlight_options(
            number_of_fragments=0, pre_tags=pre_tags, post_tags=post_tags, require_field_match=True
        )
        return super().highlight(search)


def get_archive(id):
    # try to get from cache first
    cache_key = 'archive_%s' % id
    cached = cache.get(cache_key)
    if cached:
        return cached

    archive = Archive.get(id=id)
    archive_data = archive.to_dict()
    cache.set(cache_key, archive_data)
    return archive_data


class ComponentSearchViewSet(ViewSet, PaginatedViewMixin):
    index = ComponentSearch.index
    lookup_field = 'pk'
    lookup_url_kwarg = None

    def __init__(self, *args, **kwargs):
        self.client = get_connection()
        super().__init__(*args, **kwargs)

    def get_permissions(self):
        permissions = [IsAuthenticated]
        if self.request.method in SAFE_METHODS:
            permissions.append(SearchPermissions)

        return [permission() for permission in permissions]

    def get_view_name(self):
        return 'Search {}'.format(getattr(self, 'suffix', None))

    def get_object(self, index=None):
        """
        Returns the object the view is displaying.
        """

        index = index or self.index

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        # Search for object in index by id
        id = self.kwargs[lookup_url_kwarg]

        try:
            return VersionedDocType.get(id, index=index)
        except NotFoundError:
            raise exceptions.NotFound

    def get_tag_object(self, qs=None):
        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        if qs is None:
            qs = TagVersion.objects.all()

        # Search for object in index by id
        id = self.kwargs[lookup_url_kwarg]

        prefetched_structures = TagStructure.objects.select_related(
            'tag__current_version', 'parent__tag__current_version'
        )
        tag_version = qs.select_related('tag').prefetch_related(Prefetch('tag__structures', prefetched_structures))

        obj = get_object_or_404(tag_version, pk=id)
        user_archives = get_objects_for_user(
            self.request.user,
            tag_version.filter(elastic_index='archive'), []
        ).values_list('pk', flat=True)

        root = obj.get_root()
        if root is not None and root.pk not in user_archives:
            obj_ctype = ContentType.objects.get_for_model(root)
            in_any_groups = GroupGenericObjects.objects.filter(object_id=str(root.pk), content_type=obj_ctype).exists()

            if in_any_groups:
                raise exceptions.NotFound

        logger.info(f"User '{self.request.user}' accessing tag object '{obj}'")
        return obj

    def verify_sort_field(self, field, direction='asc'):
        for f in [field, '{}.keyword'.format(field)]:
            if f in SORTABLE_FIELDS:
                return direction + f
            for sf in copy.deepcopy(SORTABLE_FIELDS):
                if isinstance(sf, dict):
                    if f in sf:
                        sf[f]['order'] = direction
                        return sf
        return False

    def get_sorting(self, request):
        sort = list()
        ordering = request.query_params.get('ordering', '').strip()
        if ordering == '':
            return sort
        fields = ordering.split(',')
        for f in fields:
            direction = 'desc' if f.startswith('-') else 'asc'
            f = remove_prefix(f, '-')
            verified_f = self.verify_sort_field(f, direction)
            if verified_f is False:
                raise exceptions.ParseError('Invalid sort field: {}'.format(f))
            sort.append(verified_f)

        return sort

    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.
        """
        pager = self.request.query_params.get('pager', None)
        if pager == 'none':
            return None

        return super().paginator

    def list(self, request):
        params = {key: value[0] for (key, value) in dict(request.query_params).items()}
        query = params.pop('q', '')
        export = params.pop('export', None)
        params.pop('pager', None)

        logger.info(f"User '{request.user}' queried for '{query}'")

        if export is not None and export not in EXPORT_FORMATS:
            raise exceptions.ParseError('Invalid export format "{}"'.format(export))

        filters = {
            'extension': params.pop('extension', None),
            'type': params.pop('type', None),
        }

        for k, v in filters.items():
            filters[k] = v.split(',') if v is not None else v

        filter_values = copy.copy(params)
        for f in ('page', 'page_size', 'ordering'):
            filter_values.pop(f, None)

        sort = self.get_sorting(request)
        s = ComponentSearch(query, filters=filters, filter_values=filter_values, sort=sort, user=self.request.user)

        if self.paginator is not None:
            # Paginate in search engine
            number = params.get(self.paginator.pager.page_query_param, 1)
            size = params.get(self.paginator.pager.page_size_query_param, 10)

            try:
                number = int(number)
            except (TypeError, ValueError):
                raise exceptions.NotFound('Invalid page.')
            if number < 1:
                raise exceptions.NotFound('Invalid page.')

            size = int(size)
            offset = (number - 1) * size
            s = s[offset:offset + size]
        else:
            s = s[0:DEFAULT_MAX_RESULT_WINDOW]

        try:
            results = s.execute()
        except TransportError:
            if self.paginator is not None:
                if offset + size > DEFAULT_MAX_RESULT_WINDOW:
                    raise exceptions.ParseError(
                        "Can't show more than {max} results".format(max=DEFAULT_MAX_RESULT_WINDOW)
                    )

            raise

        if self.paginator is not None:
            if size > 0 and results.hits.total > 0 and number > math.ceil(results.hits.total / size):
                raise exceptions.NotFound('Invalid page.')

        results_dict = results.to_dict()

        if len(results_dict['_shards'].get('failures', [])):
            return Response(results_dict['_shards']['failures'], status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        r = {
            'hits': results_dict['hits']['hits'],
            'aggregations': results_dict['aggregations'],
        }

        if export is not None:
            return self.generate_report(results_dict['hits']['hits'], export, request.user)

        return Response(r, headers={'Count': results.hits.total})

    def generate_report(self, hits, format, user):
        try:
            tag_versions = [hit.get('_source').get('name') for hit in hits]
        except Exception:
            tag_versions = hits
        logger.info(f"User '{user}' generating a {format} report, with tag versions: '{tag_versions}'")
        template = 'tags/search_results.html'.format()

        hits = [hit['_source'] for hit in hits]
        f = tempfile.TemporaryFile(mode='w+b')

        if format == 'pdf':
            ctype = 'application/pdf'
            render = render_to_string(template, {'hits': hits, 'user': user, 'timestamp': timezone.now()})
            HTML(string=render).write_pdf(f)
        elif format == 'csv':
            ctype = 'text/csv'

            text_file = io.TextIOWrapper(f, encoding='utf-8', newline='')
            writer = csv.writer(text_file)

            for hit in hits:
                writer.writerow(
                    [hit.get('archive', {}).get('name'), hit.get('name'), hit.get('reference_code'), hit.get('name'),
                     hit.get('unit_dates', {}).get('date'), hit.get('desc')])

            text_file.detach()
        else:
            raise ValueError('Unsupported format {}'.format(format))

        f.seek(0)
        name = 'search_results_{time}_{user}.{format}'.format(time=timezone.localtime(), user=user.username,
                                                              format=format)
        return generate_file_response(f, content_type=ctype, name=name)

    @action(detail=True, url_path='export')
    def archive_report(self, request, pk=None):
        archive = TagVersion.objects.get(pk=pk)
        series = archive.get_active_structure().structure.units.prefetch_related(
            Prefetch(
                'tagstructure_set',
                queryset=TagStructure.objects.select_related(
                    'tag__current_version'
                ),
                to_attr='volumes',
            ),
        ).all()

        template = 'tags/archive.html'.format()
        f = tempfile.TemporaryFile()

        ctype = 'application/pdf'
        render = render_to_string(template, {'archive_name': archive.name, 'series': series})
        HTML(string=render).write_pdf(f)

        f.seek(0)
        name = 'archive_{}.pdf'.format(pk)
        return generate_file_response(f, content_type=ctype, name=name)

    @action(detail=True, url_path='label')
    def label_report(self, request, pk=None):
        archive = TagVersion.objects.get(pk=pk)

        agents = AgentTagLink.objects.filter(tag_id=pk).all()
        series = archive.get_active_structure().structure.units.prefetch_related(
            Prefetch(
                'tagstructure_set',
                queryset=TagStructure.objects.select_related(
                    'tag__current_version'
                ),
                to_attr='volumes',
            ),
        ).all()

        template = 'tags/labels.html'.format()
        f = tempfile.TemporaryFile()

        ctype = 'application/pdf'
        render = render_to_string(template, {'archive_name': archive.name, 'series': series, 'agents': agents})
        HTML(string=render).write_pdf(f)

        f.seek(0)
        name = 'labels_{}.pdf'.format(pk)
        return generate_file_response(f, content_type=ctype, name=name)

    def serialize(self, obj):
        return obj.to_dict(include_meta=True)

    def verify_structure(self, tag_version, structure):
        query_filter = {}

        if structure is not None:
            query_filter['structure'] = structure

        try:
            if not tag_version.get_structures().filter(**query_filter).exists():
                if structure is None:
                    return None
                raise exceptions.ParseError('Structure "%s" does not exist for node' % structure)
        except ValidationError:
            raise exceptions.ParseError('Invalid structure id')

    def retrieve(self, request, pk=None):
        tag = self.get_tag_object()
        structure = self.request.query_params.get('structure')
        self.verify_structure(tag, structure)
        context = {'structure': structure, 'user': request.user}
        serialized = TagVersionSerializerWithVersions(tag, context=context).data

        return Response(serialized)

    def send_mass_email(self, ids, user):
        tags = []
        body = []
        attachments = []

        for id in ids:
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            self.kwargs[lookup_url_kwarg] = id
            tag = self.get_tag_object()
            tags.append(tag)
            metadata = tag.from_search()['_source']

            body.append('\n'.join(['{}: {}'.format(
                k, json.dumps(v, ensure_ascii=False)
            ) for k, v in metadata.items()]))

            if tag.elastic_index == 'document':
                ip = tag.tag.information_package
                path = os.path.join(metadata['href'], metadata['filename'])
                attachments.append((os.path.basename(path), ip.open_file(path, 'rb').read()))

        subject = 'Export: {}'.format(', '.join([t.name for t in tags]))
        body = '\n\n'.join(body)
        email = EmailMessage(subject=subject, body=body, to=[user.email])
        for attachment in attachments:
            email.attach(*attachment)
        email.send()
        return Response('Email sent to {}'.format(user.email))

    @action(detail=True, methods=['post'], url_path='send-as-email')
    def send_as_email(self, request, pk=None):
        tag = self.get_tag_object()
        user = self.request.user

        if not user.email:
            raise exceptions.ParseError('Missing email address')

        if request.data.get('include_descendants', False):
            ids = tag.get_descendants(include_self=True).values_list('id', flat=True)
            return self.send_mass_email(ids, user)

        metadata = tag.from_search()['_source']
        subject = 'Export: {}'.format(tag.name)

        body = '\n'.join(['{}: {}'.format(k, json.dumps(v, ensure_ascii=False)) for k, v in metadata.items()])
        email = EmailMessage(subject=subject, body=body, to=[user.email])

        if tag.elastic_index == 'document':
            ip = tag.tag.information_package
            path = os.path.join(metadata['href'], metadata['filename'])
            email.attach(os.path.basename(path), ip.open_file(path, 'rb').read())

        email.send()
        return Response('Email sent to {}'.format(user.email))

    @action(detail=False, methods=['post'], url_path='mass-email')
    def mass_email(self, request):
        try:
            ids = request.data['ids']
        except KeyError:
            raise exceptions.ParseError('Missing "ids" parameter')

        user = self.request.user
        if not user.email:
            raise exceptions.ParseError('Missing email address')

        return self.send_mass_email(ids, user)

    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        parent = self.get_tag_object()
        structure = self.request.query_params.get('structure')
        self.verify_structure(parent, structure)
        context = {'structure': structure, 'user': request.user}
        children = parent.get_children(structure)

        if self.paginator is not None:
            paginated = self.paginator.paginate_queryset(children, request)
            serialized = TagVersionNestedSerializer(instance=paginated, many=True, context=context).data
            return self.paginator.get_paginated_response(serialized)

        return Response(TagVersionNestedSerializer(children, many=True, context=context).data)

    @action(detail=True, methods=['get'], url_path='child-by-value')
    def child_by_value(self, request, pk=None):
        class ByValueSerializer(serializers.Serializer):
            field = serializers.CharField(required=True)
            value = serializers.CharField(required=True)
            structure = serializers.UUIDField(required=False)

        parent = self.get_tag_object()

        serializer = ByValueSerializer(data=request.query_params, context={'request': request.user})
        serializer.is_valid(raise_exception=True)

        field = serializer.validated_data['field']
        value = serializer.validated_data['value']
        structure = serializer.validated_data.get('structure')

        self.verify_structure(parent, structure)

        filter_values = {field: value, 'parent.id': pk}
        s = ComponentSearch('', filter_values=filter_values, user=self.request.user)
        results = s.execute().to_dict()['hits']

        if results['total'] > 1:
            raise exceptions.ParseError('More than 1 result, found {}'.format(results['total']))

        try:
            return Response(results['hits'][0])
        except IndexError:
            raise exceptions.NotFound()

    @action(detail=True, methods=['post'], url_path='new-version')
    def new_version(self, request, pk=None):
        tag = self.get_tag_object()
        tag.create_new()
        return Response()

    @action(detail=True, methods=['post'], url_path='new-structure')
    def new_structure(self, request, pk=None):
        try:
            name = request.data['name']
        except KeyError:
            raise exceptions.ParseError('Missing "name" parameter')

        with transaction.atomic():
            structure = Structure.objects.create(name=name)
            tag = self.get_tag_object()
            tag.get_active_structure().create_new(structure)

        return Response()

    @action(detail=True, methods=['patch'], url_path='set-as-current-version')
    def set_as_current_version(self, request, pk=None):
        tag = self.get_tag_object()
        tag.set_as_current_version()
        return Response()

    @action(detail=True, methods=['post'], url_path='change-organization')
    def change_organization(self, request, pk=None):
        tag = self.get_tag_object(qs=TagVersion.objects.filter(elastic_index='archive'))

        serializer = ChangeOrganizationSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        org = serializer.validated_data['organization']

        ctype = ContentType.objects.get_for_model(tag)
        self._update_tag_metadata(tag, {'organization_group': org.pk})
        GroupGenericObjects.objects.update_or_create(object_id=tag.pk, content_type=ctype,
                                                     defaults={'group': org})
        return Response()

    def create(self, request):
        index = request.data.get('index')
        organization = request.user.user_profile.current_organization

        if index == 'archive':
            if not request.user.has_perm('tags.create_archive'):
                raise exceptions.PermissionDenied('You do not have permission to create new archives')
            if organization is None:
                raise exceptions.ParseError('You must be part of an organization to create a new archive')

            serializer = ArchiveWriteSerializer(data=request.data, context={'request': request})
        elif index == 'component':
            if not request.user.has_perm('tags.add_tag'):
                raise exceptions.PermissionDenied('You do not have permission to create nodes')
            serializer = ComponentWriteSerializer(data=request.data)
        else:
            raise exceptions.ParseError('Invalid index')

        serializer.is_valid(raise_exception=True)
        tag = serializer.save()
        return Response(TagVersionNestedSerializer(instance=tag.current_version).data, status=status.HTTP_201_CREATED)

    def _update_tag_metadata(self, tag_version, data):
        if 'structure_unit' in data:
            try:
                structure = data.pop('structure')
            except KeyError:
                raise exceptions.ParseError('Missing "structure" parameter')

            structure = Structure.objects.get(pk=structure)
            tag_structure, _ = TagStructure.objects.get_or_create(tag=tag_version.tag, structure=structure)
            tag_structure.parent = tag_structure.get_root()
            tag_structure.structure_unit_id = data.get('structure_unit')
            tag_structure.save()

        elif 'parent' in data:
            try:
                structure = data.pop('structure')
            except KeyError:
                raise exceptions.ParseError('Missing "structure" parameter')

            parent = data.pop('parent')

            structure = Structure.objects.get(pk=structure)
            parent_tag_version = TagVersion.objects.get(pk=parent)
            parent_tag_structure = parent_tag_version.tag.structures.get(structure=structure)

            with transaction.atomic():
                tag_structure, _ = TagStructure.objects.get_or_create(tag=tag_version.tag, structure=structure)

                if not structure.is_move_allowed(tag_structure, parent_tag_structure):
                    raise exceptions.ParseError(
                        '{} cannot be moved to {}'.format(tag_version.name, parent_tag_version.name)
                    )

                tag_structure.parent = parent_tag_structure
                if tag_structure.parent != tag_structure.get_root():
                    tag_structure.structure_unit = None

                tag_structure.save()

        db_fields = [f.name for f in TagVersion._meta.get_fields()]
        db_fields_request_data = {}

        for f in db_fields:
            if f in data:
                db_fields_request_data[f] = data.get(f)

        serializer = TagVersionWriteSerializer(tag_version, data=db_fields_request_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        tag_version.update_search(data)
        return tag_version.from_search()

    def partial_update(self, request, pk=None):
        tag = self.get_tag_object()
        index = tag.elastic_index

        if index == 'archive':
            if not request.user.has_perm('tags.change_archive'):
                raise exceptions.PermissionDenied('You do not have permission to change archives')

            serializer = ArchiveWriteSerializer(tag, data=request.data, context={'request': request}, partial=True)
        elif index == 'component':
            data = request.data.copy()
            if 'location' in request.data:
                if not request.user.has_perm('tags.change_tag_location'):
                    raise exceptions.PermissionDenied('You do not have permission to place nodes')

                data.pop('location')

            if len(data):
                if not request.user.has_perm('tags.change_tag'):
                    raise exceptions.PermissionDenied('You do not have permission to change nodes')

            serializer = ComponentWriteSerializer(tag, data=request.data, partial=True)
        else:
            raise exceptions.ParseError('Invalid index')

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response()

    def _get_delete_field_script(self, field):
        field_path = '.'.join(field.split('.')[:-1])
        field_path = '.' + field_path if field_path else field_path
        field = field.split('.')[-1]

        return "ctx._source{path}.remove(\"{field}\")".format(path=field_path, field=field)

    def _delete_field(self, tag, field):
        index = tag.elastic_index
        script = self._get_delete_field_script(field)
        self.client.update(index=index, doc_type='doc', id=tag.pk, body={"script": script})

    @action(detail=True, methods=['post'], url_path='update-descendants')
    def update_descendants(self, request, pk=None):
        tag = self.get_tag_object()
        include_self = request.query_params.get('include_self', False)
        for descendant in tag.get_descendants(include_self=include_self):
            if descendant.elastic_index == 'archive':
                serializer = ArchiveWriteSerializer(
                    descendant, data=request.data, context={'request': request}, partial=True
                )
            elif descendant.elastic_index == 'component':
                serializer = ComponentWriteSerializer(descendant, data=request.data, partial=True)
            else:
                raise exceptions.ParseError('Invalid index')

            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response()

    @action(detail=False, methods=['post'], url_path='mass-update')
    def mass_update(self, request):
        try:
            ids = request.query_params['ids'].split(',')
        except KeyError:
            raise exceptions.ParseError('Missing "ids" parameter')

        for id in ids:
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            self.kwargs[lookup_url_kwarg] = id
            tag = self.get_tag_object()
            self._update_tag_metadata(tag, request.data)
            try:
                for field in request.query_params['deleted_fields'].split(','):
                    self._delete_field(tag, field)
            except KeyError:
                pass

        return Response()

    @action(detail=True, methods=['post'], url_path='delete-field')
    def delete_field(self, request, pk=None):
        tag = self.get_tag_object()
        try:
            field = request.data['field']
        except KeyError:
            raise exceptions.ParseError('Missing "field" parameter')

        self._delete_field(tag, field)
        return Response(tag.from_search())

    @action(detail=True, methods=['post'], url_path='remove-from-structure')
    def remove_from_structure(self, request, pk=None):
        obj = self.get_tag_object()

        if obj.elastic_index == 'archive':
            perm = 'tags.delete_archive'
        else:
            perm = 'tags.delete_tag'

        if not request.user.has_perm(perm):
            raise exceptions.PermissionDenied('You do not have permission to delete this node')

        try:
            structure = request.data['structure']
        except KeyError:
            raise exceptions.ParseError('Missing "structure" parameter')
        self.verify_structure(obj, structure)
        obj.tag.structures.get(structure=structure).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, pk=None):
        obj = self.get_tag_object()

        if obj.elastic_index == 'archive':
            perm = 'tags.delete_archive'
        else:
            perm = 'tags.delete_tag'

        if not request.user.has_perm(perm):
            raise exceptions.PermissionDenied('You do not have permission to delete this node')

        if request.query_params.get('delete_descendants', False):
            structure = request.query_params.get('structure')
            obj.get_descendants(structure=structure, include_self=True).delete()
        else:
            obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
