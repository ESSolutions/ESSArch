import copy
import csv
import datetime
import io
import json
import logging
import math
import os
import tempfile

import requests
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import models, transaction
from django.db.models import Prefetch
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_filters.constants import EMPTY_VALUES
from elasticsearch.exceptions import NotFoundError, TransportError
from elasticsearch_dsl import FacetedSearch, Q, TermsFacet
from elasticsearch_dsl.connections import get_connection
from proxy.views import proxy_view
from rest_framework import exceptions, serializers, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from weasyprint import HTML

from ESSArch_Core.agents.models import AgentTagLink
from ESSArch_Core.auth.serializers import ChangeOrganizationSerializer
from ESSArch_Core.auth.util import get_group_objs_model, get_objects_for_user
from ESSArch_Core.configuration.decorators import feature_enabled_or_404
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.maintenance.models import AppraisalJob
from ESSArch_Core.mixins import PaginatedViewMixin
from ESSArch_Core.search import DEFAULT_MAX_RESULT_WINDOW
from ESSArch_Core.tags.documents import Archive, VersionedDocType
from ESSArch_Core.tags.models import Structure, Tag, TagStructure, TagVersion
from ESSArch_Core.tags.permissions import SearchPermissions
from ESSArch_Core.tags.serializers import (
    ArchiveWriteSerializer,
    ComponentWriteSerializer,
    TagVersionNestedSerializer,
    TagVersionSerializerWithVersions,
    TagVersionWriteSerializer,
)
from ESSArch_Core.util import (
    assign_stylesheet,
    generate_file_response,
    remove_prefix,
)

EXPORT_FORMATS = ('csv', 'pdf')
SORTABLE_FIELDS = (
    {'name.keyword': {'unmapped_type': 'keyword'}},
    {'reference_code.keyword': {'unmapped_type': 'keyword'}}
)


class ComponentSearch(FacetedSearch):
    index = ['component', 'document', 'structure_unit']
    fields = [
        'reference_code.keyword^10', 'reference_code^5', 'name^2', 'desc', 'attachment.content',
        'attachment.keywords', 'archive__name',
    ]

    facets = {
        # use bucket aggregations to define facets
        'extension': TermsFacet(field='extension', min_doc_count=0, size=100),
        'type': TermsFacet(field='type', min_doc_count=0, size=100),
    }

    filters = {
        'agents': {'many': True},
        'extensions': {'many': True},
        'start_date_before': {},
        'start_date_after': {},
        'end_date_before': {},
        'end_date_after': {},
        'type': {'many': True},
        'appraisal_date_before': {},
        'appraisal_date_after': {},
    }

    def __init__(self, *args, exclude_indices=None, **kwargs):
        self.query_params_filter = kwargs.pop('filter_values', {})
        self.start_date_before = self.query_params_filter.pop('start_date_before', None)
        self.start_date_after = self.query_params_filter.pop('start_date_after', None)
        self.end_date_before = self.query_params_filter.pop('end_date_before', None)
        self.end_date_after = self.query_params_filter.pop('end_date_after', None)
        self.appraisal_date_before = self.query_params_filter.pop('appraisal_date_before', None)
        self.appraisal_date_after = self.query_params_filter.pop('appraisal_date_after', None)
        self.archives = self.query_params_filter.pop('archives', None)
        self.personal_identification_number = self.query_params_filter.pop('personal_identification_number', None)
        self.user = kwargs.pop('user')
        self.filter_values = {
            'indices': self.query_params_filter.pop('indices', [])
        }

        if exclude_indices is not None:
            self.index = [i for i in self.index if i not in exclude_indices]

        super().__init__(*args, **kwargs)

    def search(self):
        """
        We override this to add filters on archive, start and end date

        We have to manually filter archives since we want to filter against a
        script field representing the archive which is the `archive` field on
        components and `_id` on archives.
        """

        organization_archives = TagVersion.objects.filter(elastic_index='archive').for_user(self.user, [])
        organization_archives = [str(x) for x in list(organization_archives.values_list('pk', flat=True))]

        s = super().search()
        s = s.source(excludes=["attachment.content"])

        # only get current version of "TagVersion" documents
        s = s.filter('bool', minimum_should_match=1, should=[
            Q('term', current_version=True),
            Q('bool', must_not=Q('terms', _index=[
                'archive-*',
                'component-*'
            ])),
        ])

        s = s.filter(Q('bool', minimum_should_match=1, should=[
            Q('nested', path='archive', ignore_unmapped=True, query=Q('terms', archive__id=organization_archives)),
            Q('bool', must_not=[
                Q('nested', path='archive', ignore_unmapped=True, query=Q('bool', filter=Q('exists', field='archive')))
            ]),
            Q('bool', **{'must_not': {'terms': {'_index': ['component-*', 'structure_unit-*']}}}),
        ]))

        # * get everything except documents connected to IPs available to the user
        #
        # * get documents connected to any IP available to the user if the user has the
        #   permission to see files in other user's IPs. Otherwise, only get documents
        #   from IPs that the user is responsible for

        organization_ips = InformationPackage.objects.for_user(self.user, []).values_list('pk', flat=True)

        if self.user.has_perm('ip.see_other_user_ip_files'):
            document_ips = organization_ips
        else:
            document_ips = self.user.information_packages.values_list('pk', flat=True)

        s = s.filter(Q('bool', minimum_should_match=1, should=[
            Q('bool', must=[
                Q('bool', minimum_should_match=1, should=[
                    ~Q('exists', field='ip'),
                    Q('terms', ip=list(organization_ips))
                ]),
                Q('bool', **{'must_not': {'terms': {'_index': ['document-*']}}}),
            ]),
            Q('bool', must=[
                Q('terms', _index=['document-*']),
                Q('bool', minimum_should_match=1, should=[~Q('exists', field='ip'), Q('terms', ip=list(document_ips))])
            ]),
        ]))

        user_security_level_perms = list(filter(
            lambda x: x.startswith('tags.security_level_'),
            self.user.get_all_permissions(),
        ))

        if len(user_security_level_perms) > 0:
            user_security_levels = list(map(lambda x: int(x[-1]), user_security_level_perms))
            s = s.filter(Q('bool', minimum_should_match=1, should=[
                Q('terms', security_level=user_security_levels),
                Q('bool', must_not=Q('exists', field='security_level')),
            ]))
        else:
            s = s.filter(Q('bool', minimum_should_match=1, should=[
                Q('bool', must_not=Q('exists', field='security_level')),
            ]))

        if self.personal_identification_number not in EMPTY_VALUES:
            s = s.filter('term', personal_identification_number=self.personal_identification_number)

        if self.start_date_after not in EMPTY_VALUES:
            s = s.filter('range', start_date={'gte': self.start_date_after - datetime.timedelta(days=1)})

        if self.start_date_before not in EMPTY_VALUES:
            s = s.filter('range', start_date={'lte': self.start_date_before - datetime.timedelta(days=1)})

        if self.end_date_after not in EMPTY_VALUES:
            s = s.filter('range', end_date={'gte': self.end_date_after - datetime.timedelta(days=1)})

        if self.end_date_before not in EMPTY_VALUES:
            s = s.filter('range', end_date={'lte': self.end_date_before - datetime.timedelta(days=1)})

        if self.appraisal_date_after not in EMPTY_VALUES:
            s = s.filter('range', appraisal_date={'gte': self.appraisal_date_after - datetime.timedelta(days=1)})

        if self.appraisal_date_before not in EMPTY_VALUES:
            s = s.filter('range', appraisal_date={'lte': self.appraisal_date_before - datetime.timedelta(days=1)})

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

    def query(self, search, query):
        """
        Add query part to ``search``.

        Overrided to support nested fields, currently only supports one level.
        """

        if query:
            nested_queries = []
            fields = []

            for field in self.fields:
                if '__' in field:
                    paths = field.split('__')
                    for idx, _path in enumerate(paths):
                        if idx == 0:
                            continue

                        subquery = {
                            "path": paths[idx - 1],
                            "ignore_unmapped": True,
                            "query": Q("match", **{'.'.join(paths[:idx + 1]): query})
                        }

                    nested_queries.append(Q('nested', **subquery))
                else:
                    fields.append(field)

            queries = nested_queries + [Q('multi_match', fields=fields, query=query)]
            return search.query('bool', minimum_should_match=1, should=queries)
        return search

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


class ComponentSearchSerializer(serializers.Serializer):
    appraisal_date_before = serializers.DateField(required=False, allow_null=True, default=None)
    appraisal_date_after = serializers.DateField(required=False, allow_null=True, default=None)
    start_date_before = serializers.DateField(required=False, allow_null=True, default=None)
    start_date_after = serializers.DateField(required=False, allow_null=True, default=None)
    end_date_before = serializers.DateField(required=False, allow_null=True, default=None)
    end_date_after = serializers.DateField(required=False, allow_null=True, default=None)

    def validate(self, data):
        if (data['appraisal_date_after'] and data['appraisal_date_before'] and
                data['appraisal_date_after'] > data['appraisal_date_before']):

            raise serializers.ValidationError("appraisal_date_after must occur before appraisal_date_before")

        if (data['start_date_after'] and data['start_date_before'] and
                data['start_date_after'] > data['start_date_before']):

            raise serializers.ValidationError("start_date_after must occur before start_date_before")

        if (data['end_date_after'] and data['end_date_before'] and
                data['end_date_after'] > data['end_date_before']):

            raise serializers.ValidationError("end_date_after must occur before end_date_before")

        return data


@method_decorator(feature_enabled_or_404('archival descriptions'), name='initial')
class ComponentSearchViewSet(ViewSet, PaginatedViewMixin):
    index = ComponentSearch.index
    lookup_field = 'pk'
    lookup_url_kwarg = None
    serializer_class = ComponentSearchSerializer

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

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        return serializer_class(*args, **kwargs)

    def get_serializer_class(self):
        return self.serializer_class

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
        logger = logging.getLogger('essarch.search')
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        if qs is None:
            qs = TagVersion.objects.for_user(self.request.user, [])

        # Search for object in index by id
        id = self.kwargs[lookup_url_kwarg]

        prefetched_structures = TagStructure.objects.select_related(
            'tag__current_version', 'parent__tag__current_version'
        )
        tag_version = qs.select_related('tag').prefetch_related(Prefetch('tag__structures', prefetched_structures))

        if not self.request.user.has_perm('ip.see_other_user_ip_files'):
            tag_version = tag_version.exclude(
                ~models.Q(tag__information_package__responsible=self.request.user),
                elastic_index='document',
            )

        obj = get_object_or_404(tag_version, pk=id)
        root = obj.get_root()
        user_archives = get_objects_for_user(
            self.request.user,
            tag_version.filter(elastic_index='archive'), []
        )

        if root is not None:
            root_in_archives = user_archives.filter(pk=str(root.pk)).exists()
            if not root_in_archives:
                group_objs_model = get_group_objs_model(root)
                in_any_groups = group_objs_model.objects.get_organization(root, list=True).exists()
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
        logger = logging.getLogger('essarch.search')
        params = {key: value[0] for (key, value) in dict(request.query_params).items()}
        query = params.pop('q', '')
        export = params.pop('export', None)
        add_to_appraisal = params.pop('add_to_appraisal', None)
        params.pop('pager', None)

        logger.info(f"User '{request.user}' queried for '{query}'")

        if export is not None and add_to_appraisal is not None:
            raise exceptions.ParseError('Cannot both export results and add to appraisal')

        if export is not None and export not in EXPORT_FORMATS:
            raise exceptions.ParseError('Invalid export format "{}"'.format(export))

        if add_to_appraisal is not None:
            try:
                appraisal_job = AppraisalJob.objects.get(pk=add_to_appraisal)
            except AppraisalJob.DoesNotExist:
                raise exceptions.ParseError('Appraisal job with id "{}" does not exist'.format(add_to_appraisal))
        else:
            appraisal_job = None

        filters = {
            'extension': params.pop('extension', None),
            'type': params.pop('type', None),
        }

        for k, v in filters.items():
            filters[k] = v.split(',') if v is not None else v

        filter_values = copy.copy(params)
        for f in ('page', 'page_size', 'ordering'):
            filter_values.pop(f, None)

        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filter_values.update(serializer.validated_data)

        sort = self.get_sorting(request)
        exclude_indices = None

        if appraisal_job is not None:
            exclude_indices = ['structure_unit']

        s = ComponentSearch(
            query, filters=filters, filter_values=filter_values, sort=sort, user=self.request.user,
            exclude_indices=exclude_indices,
        )

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
            if size > 0 and results.hits.total['value'] > 0 and number > math.ceil(results.hits.total['value'] / size):
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

        if appraisal_job is not None:
            ids = [hit['_id'] for hit in results_dict['hits']['hits']]
            tags = Tag.objects.filter(versions__in=ids)
            appraisal_job.tags.add(*tags)
            return Response()

        return Response(r, headers={'Count': results.hits.total['value']})

    def generate_report(self, hits, format, user):
        logger = logging.getLogger('essarch.search')
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
        agents = AgentTagLink.objects.filter(tag_id=pk).all()
        archive = TagVersion.objects.get(pk=pk)
        structure_id = request.query_params['structure']
        structure = Structure.objects.get(pk=structure_id)

        series = structure.units.prefetch_related(
            Prefetch(
                'tagstructure_set',
                queryset=TagStructure.objects.select_related(
                    'tag__current_version'
                ),
                to_attr='volumes',
            ),
        ).all().order_by('reference_code')

        template = 'tags/archive.html'.format()
        f = tempfile.TemporaryFile()

        ctype = 'application/pdf'
        render = render_to_string(template, {'agents': agents, 'archive': archive, 'series': series})
        HTML(string=render).write_pdf(f)

        f.seek(0)
        name = 'archive_{}.pdf'.format(pk)
        return generate_file_response(f, content_type=ctype, name=name)

    @action(detail=True, url_path='xml2pdf')
    def xml2pdf(self, request, pk=None):
        obj = TagVersion.objects.get(pk=pk)
        xslt = os.path.join(settings.MEDIA_ROOT, str(obj.rendering.file))
        ip_file_path = os.path.join(obj.custom_fields['href'], obj.custom_fields['filename'])
        xml = obj.tag.information_package.open_file(ip_file_path)

        transformed_doc = assign_stylesheet(xml, xslt)

        ctype = 'application/pdf'
        f = tempfile.TemporaryFile()
        HTML(string=transformed_doc).write_pdf(f)
        name = '{}_{}.pdf'.format(str(obj.rendering.file), pk)
        return generate_file_response(f, content_type=ctype, name=name)

    @action(detail=True, url_path='label')
    def label_report(self, request, pk=None):
        archive = TagVersion.objects.get(pk=pk)
        agents = AgentTagLink.objects.filter(tag_id=pk).all()
        structure_id = request.query_params['structure']
        structure = Structure.objects.get(pk=structure_id)

        series = structure.units.prefetch_related(
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
        context = {'structure': structure, 'request': request, 'user': request.user}
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

    @action(detail=False, methods=['get'], url_path='omeka_api/(?P<path>.*)')
    def omeka_api(self, request, path):
        omeka_key = getattr(settings, 'OMEKA_KEY', '')
        if omeka_key:
            extra_requests_args = {'params': {'key': omeka_key}}
        else:
            extra_requests_args = {}
        omeka_server = getattr(settings, 'OMEKA_SERVER', 'https://localhost')
        remoteurl = '%s/api/%s' % (omeka_server, path)
        return proxy_view(request, remoteurl, extra_requests_args)

    @action(detail=True, methods=['post'], url_path='export-to-omeka')
    def export_to_omeka(self, request, pk=None):
        tag = self.get_tag_object()
        metadata = tag.from_search()['_source']

        # Create item in collection
        collection_id = request.data.get('collection_id', None)
        item_id = self.create_item(collection_id, metadata)
        print('item_id: %s' % item_id)

        # Upload file to item
        if tag.elastic_index == 'document':
            ip = tag.tag.information_package
            path = os.path.join(metadata['href'], metadata['filename'])
            file_item = ip.open_file(path, 'rb').read()
            file_order = 1
            self.upload_file(file_order, item_id, file_item, metadata)
        return Response('Exported to Omeka (collection id: {})'.format(request.data.get('collection_id', '-')))

    def create_item(self, collection_id, metadata):
        omeka_server = getattr(settings, 'OMEKA_SERVER', 'https://localhost')
        url = '%s/api/items' % omeka_server
        omeka_key = getattr(settings, 'OMEKA_KEY', '')
        if omeka_key:
            params = {'key': omeka_key}
        else:
            params = {}
        metadata_title = '%s - %s' % (metadata['structure_units'][0]['name'],
                                      metadata['structure_units'][0]['reference_code'])

        data = {
            "item_type": {"id": 1},
            "collection": {"id": collection_id},
            "public": True,
            "featured": False,
            "tags": [
                {"name": metadata['archive']['name']},
                {"name": metadata['archive']['reference_code']}
            ],
            "element_texts": [
                {
                    "html": False,
                    "text": metadata_title,
                    "element": {"id": 50}  # ID of the element responsible for title (50 in Dublin Core)
                }
            ]
        }

        response = requests.post(url, params=params, data=json.dumps(data))
        item_id = json.loads(response.content)['id']

        return item_id

    def upload_file(self, order, item_id, file_item, metadata):
        omeka_server = getattr(settings, 'OMEKA_SERVER', 'https://localhost')
        url = '%s/api/files' % omeka_server
        omeka_key = getattr(settings, 'OMEKA_KEY', '')
        if omeka_key:
            params = {'key': omeka_key}
        else:
            params = {}

        # Building data structure for the request
        body_data = {
            "order": order,  # order of the file, integer
            "item": {"id": item_id},  # ID of the item to which the file should be attached
            "element_texts": [
                    {
                        "html": False,
                        "text": metadata['name'],  # Title of the document
                        "element": {"id": 50}  # ID of the element responsible for title (50 in Dublin Core)
                    }
            ]
        }
        data = {'data': json.dumps(body_data)}  # packing body data to json and assigning name 'data' to it

        # Building info about my file, assigning name 'file'
        files = {
            'file': (metadata['filename'],
                     file_item,
                     'application/png')
        }
        requests.post(url, params=params, data=data, files=files)

    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        parent = self.get_tag_object()
        structure = self.request.query_params.get('structure')
        self.verify_structure(parent, structure)
        context = {'structure': structure, 'request': request, 'user': request.user, 'is_mixed_type': False}
        children = parent.get_children(structure).select_related(
            'tag__information_package', 'type',
        ).prefetch_related(
            'agent_links', 'identifiers', 'notes', 'tag_version_relations_a',
        ).for_user(request.user)
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

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='change-organization')
    def change_organization(self, request, pk=None):
        tag = self.get_tag_object(qs=TagVersion.objects.filter(elastic_index='archive'))

        serializer = ChangeOrganizationSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        organization = serializer.validated_data['organization']
        force = serializer.validated_data['force']
        change_related_StructureUnits = serializer.validated_data['change_related_StructureUnits']
        change_related_StructureUnits_force = serializer.validated_data['change_related_StructureUnits_force']
        change_related_Nodes = serializer.validated_data['change_related_Nodes']
        change_related_Nodes_force = serializer.validated_data['change_related_Nodes_force']
        change_related_IPs = serializer.validated_data['change_related_IPs']
        change_related_IPs_force = serializer.validated_data['change_related_IPs_force']
        change_related_AIDs = serializer.validated_data['change_related_AIDs']
        change_related_AIDs_force = serializer.validated_data['change_related_AIDs_force']

        tag.change_organization(organization, force=force,
                                change_related_StructureUnits=change_related_StructureUnits,
                                change_related_StructureUnits_force=change_related_StructureUnits_force,
                                change_related_Nodes=change_related_Nodes,
                                change_related_Nodes_force=change_related_Nodes_force,
                                change_related_IPs=change_related_IPs,
                                change_related_IPs_force=change_related_IPs_force,
                                change_related_AIDs=change_related_AIDs,
                                change_related_AIDs_force=change_related_AIDs_force)

        return Response()

    def create(self, request):
        class TagVersionCreationSerializer(serializers.Serializer):
            index = serializers.CharField()

        serializer = TagVersionCreationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        index = data.get('index')
        organization = request.user.user_profile.current_organization

        if index == 'archive':
            if not request.user.has_perm('tags.create_archive'):
                raise exceptions.PermissionDenied('You do not have permission to create new archives')
            if organization is None:
                raise exceptions.ParseError('You must be part of an organization to create a new archive')

            serializer = ArchiveWriteSerializer(data=request.data, context={'request': request})
        elif index in ['component', 'document']:
            if not request.user.has_perm('tags.add_tag'):
                raise exceptions.PermissionDenied('You do not have permission to create nodes')
            serializer = ComponentWriteSerializer(data=request.data)
        else:
            raise exceptions.ParseError('Invalid index')

        serializer.is_valid(raise_exception=True)
        tag = serializer.save()
        return Response(
            TagVersionNestedSerializer(instance=tag.current_version, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

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
        elif index in ['component', 'document']:
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
            elif descendant.elastic_index in ['component', 'document']:
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

        if obj.elastic_index == 'archive' and obj.tag.versions.count() == 1:
            structures = Structure.objects.filter(
                tagstructure__tag=obj.tag,
                is_template=False,
            ).values_list('pk', flat=True)
            structures = list(structures)
            Tag.objects.filter(structures__structure__tagstructure__tag=obj.tag).delete()
            Structure.objects.filter(pk__in=structures).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        if obj.tag.versions.count() == 1 or request.query_params.get('delete_descendants', False):
            structure = request.query_params.get('structure')
            obj.get_descendants(structure=structure, include_self=True).delete()
        else:
            obj.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
