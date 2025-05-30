import copy
import errno
import glob
import io
import itertools
import json
import logging
import math
import os
import shutil
import tarfile
import uuid
import zipfile

from celery import states as celery_states
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import (
    BooleanField,
    Case,
    Exists,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
    When,
)
from django.http import Http404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext
from django_filters.constants import EMPTY_VALUES
from django_filters.rest_framework import DjangoFilterBackend
from elasticsearch.exceptions import TransportError
from elasticsearch_dsl import Index, Q as ElasticQ, Search
from groups_manager.utils import get_permission_name
from guardian.shortcuts import assign_perm
from lxml import etree
from rest_framework import (
    exceptions,
    filters,
    mixins,
    permissions,
    status,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.api.filters import string_to_bool
from ESSArch_Core.auth.decorators import permission_required_or_403
from ESSArch_Core.auth.models import Member
# from ESSArch_Core.auth.permission_checker import ObjectPermissionChecker
from ESSArch_Core.auth.permissions import ActionPermissions
from ESSArch_Core.auth.serializers import ChangeOrganizationSerializer
from ESSArch_Core.configuration.decorators import feature_enabled_or_404
from ESSArch_Core.configuration.models import Path
from ESSArch_Core.essxml.Generator.xmlGenerator import parseContent
from ESSArch_Core.essxml.util import get_objectpath, parse_submit_description
from ESSArch_Core.exceptions import Conflict, NoFileChunksFound
from ESSArch_Core.fixity.format import FormatIdentifier
from ESSArch_Core.fixity.models import ActionTool
from ESSArch_Core.fixity.transformation import AVAILABLE_TRANSFORMERS
from ESSArch_Core.fixity.validation import AVAILABLE_VALIDATORS
from ESSArch_Core.fixity.validation.backends.checksum import ChecksumValidator
from ESSArch_Core.ip.filters import (
    AgentFilter,
    EventIPFilter,
    InformationPackageFilter,
    WorkareaEntryFilter,
)
from ESSArch_Core.ip.models import (
    Agent,
    ConsignMethod,
    EventIP,
    InformationPackage,
    Order,
    OrderType,
    Workarea,
)
from ESSArch_Core.ip.permissions import (
    CanChangeSA,
    CanCreateSIP,
    CanDeleteIP,
    CanSetUploaded,
    CanSubmitSIP,
    CanTransferSIP,
    CanUnlockProfile,
    CanUpload,
    IsOrderResponsibleOrAdmin,
    IsResponsibleOrCanSeeAllFiles,
    IsResponsibleOrReadOnly,
)
from ESSArch_Core.ip.serializers import (
    ActionToolSerializer,
    AgentSerializer,
    ConsignMethodSerializer,
    EventIPSerializer,
    EventIPWriteSerializer,
    InformationPackageCreateSerializer,
    InformationPackageDetailSerializer,
    InformationPackageFromMasterSerializer,
    InformationPackageSerializer,
    InformationPackageUpdateSerializer,
    NestedInformationPackageSerializer,
    OrderSerializer,
    OrderTypeSerializer,
    OrderWriteSerializer,
    WorkareaSerializer,
)
from ESSArch_Core.ip.utils import parse_submit_description_from_ip
from ESSArch_Core.mixins import PaginatedViewMixin
from ESSArch_Core.profiles.models import (
    Profile,
    ProfileIP,
    SubmissionAgreement,
)
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.search import DEFAULT_MAX_RESULT_WINDOW
from ESSArch_Core.util import (
    creation_date,
    find_destination,
    generate_file_response,
    get_immediate_subdirectories,
    get_value_from_path,
    in_directory,
    list_files,
    merge_file_chunks,
    normalize_path,
    parse_content_range_header,
    remove_prefix,
    timestamp_to_datetime,
    zip_directory,
)
from ESSArch_Core.WorkflowEngine.filters import (
    ProcessStepFilter,
    ProcessTaskFilter,
)
from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask
from ESSArch_Core.WorkflowEngine.serializers import (
    ProcessStepChildrenSerializer,
)
from ESSArch_Core.WorkflowEngine.util import create_workflow

User = get_user_model()


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    filter_backends = (filters.OrderingFilter, DjangoFilterBackend, SearchFilter,)
    filterset_class = AgentFilter


class ConsignMethodViewSet(viewsets.ModelViewSet):
    queryset = ConsignMethod.objects.all()
    serializer_class = ConsignMethodSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (filters.OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)


class EventIPViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows events to be viewed or edited.
    """
    queryset = EventIP.objects.all()
    serializer_class = EventIPSerializer
    permission_classes = (ActionPermissions,)
    filterset_class = EventIPFilter
    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend, SearchFilter,
    )
    ordering_fields = (
        'id', 'eventType', 'eventOutcomeDetailNote', 'eventOutcome',
        'linkingAgentIdentifierValue', 'eventDateTime',
    )
    search_fields = ('eventOutcomeDetailNote',)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return EventIPWriteSerializer

        return self.serializer_class

    def filter_queryset_by_parents_lookups(self, queryset):
        '''
        We want to filter events directly connected to deliveries and through transfers, i.e.
        api/deliveries/{id}/events/ should list events both connected to the delivery and its transfers.

        We do this by extracting the delivery parent query key from the dict made by drf-extensions
        and then manually creating the query. The rest of the keys in the dict is handled as usual.
        '''

        parents_query_dict = self.get_parents_query_dict()
        delivery = parents_query_dict.pop('delivery', None)

        if delivery is not None:
            queryset = queryset.filter(Q(delivery=delivery) | Q(transfer__delivery=delivery))

        if parents_query_dict:
            try:
                return queryset.filter(**parents_query_dict)
            except ValueError:
                raise Http404
        else:
            return queryset


class WorkareaEntryViewSet(mixins.DestroyModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Workarea.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WorkareaSerializer

    def get_queryset(self):
        see_all = self.request.user.has_perm('ip.see_all_in_workspaces')
        ips = InformationPackage.objects.visible_to_user(self.request.user)

        qs = super().get_queryset().filter(ip__in=ips)
        if not see_all:
            qs = qs.filter(user=self.request.user)

        return qs

    @action(detail=True, methods=['post'], url_path='actiontool')
    def actiontool(self, request, pk=None):
        workarea: Workarea = self.get_object()

        serializer = ActionToolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        workflow_spec = []

        for action_data in serializer.validated_data['actions']:
            tool_name = action_data['name']

            # ensure that tool exists
            action_tool = ActionTool.objects.get(name=tool_name)

            options = action_data['options']
            pattern = None

            if 'path' in action_data:
                pattern = action_data['path']

            if action_tool.environment == "task":
                tool_cmd = json.loads(action_tool.cmd)
                tool_cmd.update(options)

                workflow_spec.append({
                    "name": action_tool.path,
                    "label": tool_name,
                    "params": tool_cmd
                })

            else:
                workflow_spec.append({
                    "name":
                    "ESSArch_Core.fixity.action.tasks.Action",
                    "label":
                    tool_name,
                    "args": [
                        tool_name, pattern, workarea.path, options, request.data.get('purpose')
                    ]
                })

        workflow = create_workflow(workflow_spec, eager=False, ip=workarea.ip, name='Action tool')
        workflow.run()
        return Response()

    @action(detail=True, methods=['post'], url_path='validate')
    def validate(self, request, pk=None):
        workarea = self.get_object()
        ip = workarea.ip
        task_name = "ESSArch_Core.tasks.ValidateWorkarea"

        if ip.get_profile('validation') is None:
            raise exceptions.ParseError("IP does not have a \"validation\" profile")

        if ProcessTask.objects.filter(information_package=ip, name=task_name, time_done__isnull=True).exists():
            raise exceptions.ParseError(
                '"{objid}" is already being validated'.format(objid=ip.object_identifier_value)
            )

        ip.validation_set.all().delete()

        stop_at_failure = request.data.get('stop_at_failure', False)
        validators = request.data.get('validators', {})
        available_validators = AVAILABLE_VALIDATORS.keys()

        if not any(selected in available_validators for selected in validators):
            raise exceptions.ParseError('No valid validator selected')

        for selected in validators:
            if selected not in available_validators:
                raise exceptions.ParseError('Validator "%s" not found' % selected)
            if selected not in ip.get_profile('validation').specification.keys():
                raise exceptions.ParseError('Validator "%s" not specified in validation profile' % selected)

        params = {'validators': validators, 'stop_at_failure': stop_at_failure}

        task = ProcessTask.objects.create(
            name=task_name,
            args=[pk],
            params=params,
            eager=False,
            log=EventIP,
            information_package=ip,
            responsible=self.request.user,
        )
        task.run()
        return Response("Validating IP")

    @action(detail=True, methods=['post'], url_path='transform')
    def transform(self, request, pk=None):
        workarea = self.get_object()
        ip = workarea.ip

        if ip.state.lower() in ('transforming', 'transformed'):
            raise exceptions.ParseError(
                "\"{ip}\" already {state}".format(ip=ip.object_identifier_value, state=ip.state.lower())
            )

        transformer = request.data.get('transformer')
        if transformer is None:
            raise exceptions.ParseError("Missing transformer parameter")

        if transformer not in AVAILABLE_TRANSFORMERS:
            raise exceptions.ParseError("Transformer {} not in config".format(transformer))

        if ip.get_profile('validation') is not None:
            for validator, successful in workarea.successfully_validated.items():
                if successful is not True:
                    raise exceptions.ParseError(
                        "\"{ip}\" hasn't been successfully validated with \"{validator}\"".format(
                            ip=ip.object_identifier_value, validator=validator
                        )
                    )

        step = ProcessStep.objects.create(name="Transform", eager=False, information_package=ip)
        pos = 0

        ProcessTask.objects.create(
            name="ESSArch_Core.tasks.UpdateIPStatus",
            args=["Transforming"],
            processstep=step,
            processstep_pos=pos,
            log=EventIP,
            information_package=ip,
            responsible=request.user,
        )

        pos += 10

        ProcessTask.objects.create(
            name="ESSArch_Core.tasks.TransformWorkarea",
            args=[transformer, pk],
            log=EventIP,
            processstep=step,
            processstep_pos=pos,
            information_package=ip,
            responsible=request.user,
        )

        pos += 10

        ProcessTask.objects.create(
            name="ESSArch_Core.tasks.UpdateIPStatus",
            args=["Transformed"],
            processstep=step,
            processstep_pos=pos,
            log=EventIP,
            information_package=ip,
            responsible=request.user,
        )
        step.run()

        return Response("Transforming IP")

    def destroy(self, request, pk=None, **kwargs):
        workarea = self.get_object()

        if not workarea.read_only and not workarea.ip.archived:
            workarea.delete_files()
            workarea.delete_temp_files()
            workarea.ip.delete_files()
            workarea.ip.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return super().destroy(request, pk, **kwargs)


class InformationPackageViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows information packages to be viewed or edited.
    """

    logger = logging.getLogger('essarch.InformationPackageViewSet')

    queryset = InformationPackage.objects.none()
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = InformationPackageSerializer
    filter_backends = (filters.OrderingFilter, DjangoFilterBackend, SearchFilter,)
    ordering_fields = (
        'label', 'responsible', 'create_date', 'state',
        'id', 'object_identifier_value', 'start_date', 'end_date',
    )
    search_fields = (
        '^object_identifier_value', '^label',
    )
    filterset_class = InformationPackageFilter

    def get_permissions(self):
        if self.action in ['partial_update', 'update']:
            if self.request.data.get('submission_agreement'):
                self.permission_classes = [CanChangeSA]
        if self.action == 'destroy':
            self.permission_classes = [CanDeleteIP]

        return super().get_permissions()

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        lookup_field = self.lookup_field

        objid = self.request.query_params.get('objid')
        if objid is not None:
            lookup_field = 'object_identifier_value'

        filter_kwargs = {lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    @staticmethod
    def annotate_generations(qs):
        lower_higher = InformationPackage.objects.filter(
            Q(aic=OuterRef('aic')), Q(Q(workareas=None) | Q(workareas__read_only=True) | Q(archived=True))
        ).exclude(state='Ingest Workspace', archived=False).order_by().values('aic')
        lower_higher = lower_higher.annotate(min_gen=Min('generation'), max_gen=Max('generation'))

        return qs.annotate(first_generation=InformationPackageViewSet.first_generation_case(lower_higher),
                           last_generation=InformationPackageViewSet.last_generation_case(lower_higher))

    def annotate_filtered_first_generation(self, qs, user):
        lower_higher = InformationPackage.objects.visible_to_user(user).filter(
            Q(Q(workareas=None) | Q(workareas__read_only=True) | Q(archived=True)),
            aic=OuterRef('aic'),
        ).order_by().values('aic')
        lower_higher = self.apply_filters(queryset=lower_higher).order_by()
        lower_higher = lower_higher.annotate(min_gen=Min('generation'))
        return qs.annotate(filtered_first_generation=self.first_generation_case(lower_higher))

    def get_related(self, qs, workareas):
        qs = qs.select_related('responsible')
        return qs.prefetch_related(
            Prefetch('agents', queryset=Agent.objects.prefetch_related('notes'), to_attr='prefetched_agents'),
            'steps', Prefetch('workareas', queryset=workareas, to_attr='prefetched_workareas'))

    def get_queryset(self):
        view_type = self.request.query_params.get('view_type', 'aic')
        user = self.request.user
        see_all = self.request.user.has_perm('ip.see_all_in_workspaces')

        workarea_params = {}
        for key, val in self.request.query_params.items():
            if key.startswith('workspace_'):
                key_suffix = remove_prefix(key, 'workspace_')
                workarea_params[key_suffix] = val

        workareas = Workarea.objects.all()
        workareas = WorkareaEntryFilter(data=workarea_params, queryset=workareas, request=self.request).qs
        if not see_all:
            workareas = workareas.filter(user=self.request.user)

        if not self.detail and view_type == 'aic':
            simple_inner = InformationPackage.objects.visible_to_user(user).exclude(
                Q(state='Ingest Workspace') |
                Q(Q(workareas__isnull=False) & Q(workareas__read_only=False) & Q(archived=False))
            )

            simple_inner = self.apply_filters(simple_inner).order_by(*InformationPackage._meta.ordering)

            inner = simple_inner.select_related('responsible').prefetch_related(
                'agents', 'steps',
                Prefetch('workareas', queryset=workareas, to_attr='prefetched_workareas')
            )
            dips_and_sips = inner.filter(package_type__in=[InformationPackage.DIP, InformationPackage.SIP])

            lower_higher = InformationPackage.objects.filter(
                Q(aic=OuterRef('aic')), Q(Q(workareas=None) | Q(workareas__read_only=True) | Q(archived=True))
            ).order_by().values('aic')
            lower_higher = lower_higher.annotate(min_gen=Min('generation'), max_gen=Max('generation'))

            inner = inner.annotate(first_generation=self.first_generation_case(lower_higher),
                                   last_generation=self.last_generation_case(lower_higher))

            simple_outer = InformationPackage.objects.annotate(
                has_ip=Exists(
                    simple_inner.only('id').filter(
                        aic=OuterRef('pk')
                    )
                )
            ).filter(
                package_type=InformationPackage.AIC, has_ip=True
            )
            profile_ips = ProfileIP.objects.select_related(
                'profile', 'ip', 'data',
            ).prefetch_related('data_versions')

            inner = inner.prefetch_related(
                Prefetch('profileip_set', queryset=profile_ips,)
            )
            simple_outer = simple_outer.prefetch_related(
                Prefetch('profileip_set', queryset=profile_ips,)
            )

            aics = simple_outer.prefetch_related(Prefetch('information_packages', queryset=inner))

            if self.apply_ordering_filters(aics):
                self.queryset = self.apply_ordering_filters(aics)
            else:
                self.queryset = self.apply_filters(dips_and_sips)
            # self.outer_queryset = simple_outer | dips_and_sips
            # self.inner_queryset = simple_inner
            return self.queryset
        elif not self.detail and view_type == 'ip':
            filtered = InformationPackage.objects.visible_to_user(user).exclude(
                Q(Q(state='Ingest Workspace') | Q(package_type=InformationPackage.AIC)) |
                Q(Q(workareas__isnull=False) & Q(workareas__read_only=False) & Q(archived=False))
            )

            simple = self.apply_filters(filtered)
            simple = self.annotate_generations(simple)
            simple = self.annotate_filtered_first_generation(simple, user)
            simple = self.get_related(simple, workareas)
            simple = simple.select_related(
                'responsible',
                'submission_agreement__policy__cache_storage',
                'submission_agreement__policy__ingest_path',
            )

            profile_ips = ProfileIP.objects.select_related(
                'profile', 'ip', 'data',
            ).prefetch_related('data_versions')

            inner = simple.filter(filtered_first_generation=False).prefetch_related(
                Prefetch('profileip_set', queryset=profile_ips,)
            )
            outer = simple.filter(filtered_first_generation=True).prefetch_related(
                Prefetch('aic__information_packages', queryset=inner)
            )

            # self.inner_queryset = simple
            # self.outer_queryset = simple
            self.queryset = outer
            return self.queryset
        elif not self.detail and view_type == 'flat':
            filtered = InformationPackage.objects.visible_to_user(user).exclude(
                Q(Q(state='Ingest Workspace') | Q(package_type=InformationPackage.AIC)) |
                Q(Q(workareas__isnull=False) & Q(workareas__read_only=False) & Q(archived=False))
            )

            qs = self.apply_filters(filtered)

            profile_ips = ProfileIP.objects.select_related(
                'profile', 'ip', 'data',
            ).prefetch_related('data_versions')
            qs = qs.select_related(
                'responsible', 'submission_agreement__policy__cache_storage',
                'submission_agreement__policy__ingest_path'
            ).prefetch_related(
                'agents', 'steps',
                Prefetch('workareas', queryset=workareas, to_attr='prefetched_workareas'),
                Prefetch('profileip_set', queryset=profile_ips,),
            )
            qs = self.annotate_generations(qs)

            self.queryset = qs
            return self.queryset

        elif not self.detail:
            raise exceptions.ParseError('Invalid view type')

        if self.detail:
            lower_higher = InformationPackage.objects.filter(
                Q(aic=OuterRef('aic')), Q(Q(workareas=None) | Q(workareas__read_only=True) | Q(archived=True))
            ).order_by().values('aic')
            lower_higher = lower_higher.annotate(min_gen=Min('generation'), max_gen=Max('generation'))

            qs = InformationPackage.objects.visible_to_user(user).filter(
                Q(Q(workareas=None) | Q(workareas__read_only=True) | Q(archived=True)),
            )

            qs = self.apply_filters(qs)
            qs = qs.annotate(first_generation=self.first_generation_case(lower_higher),
                             last_generation=self.last_generation_case(lower_higher))
            qs = qs.select_related('responsible').prefetch_related(
                'agents', 'steps',
                Prefetch('workareas', queryset=workareas, to_attr='prefetched_workareas')
            )
            self.queryset = qs.distinct()
            return self.queryset

        return self.queryset

    @action(detail=True, methods=['post'], url_path='change-organization')
    def change_organization(self, request, pk=None):
        ip = self.get_object()

        serializer = ChangeOrganizationSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        org = serializer.validated_data['organization']

        if ip.get_organization() is None:
            force = True
        else:
            force = False
        ip.change_organization(org, force)
        return Response()

    @action(detail=True)
    def workflow(self, request, pk=None):
        ip = self.get_object()

        steps = ip.steps.filter(parent__information_package__isnull=True)
        tasks = ip.processtask_set.filter(processstep__information_package__isnull=True)

        steps = ProcessStepFilter(data=request.query_params, queryset=steps, request=self.request).qs
        tasks = ProcessTaskFilter(data=request.query_params, queryset=tasks, request=self.request).qs

        flow = sorted(itertools.chain(steps, tasks), key=lambda x: (x.time_created, x.get_pos()))

        if self.paginator is not None:
            paginated = self.paginator.paginate_queryset(flow, request)
            serializer = ProcessStepChildrenSerializer(data=paginated, many=True, context={'request': request})
            serializer.is_valid()
            return self.paginator.get_paginated_response(serializer.data)

        serializer = ProcessStepChildrenSerializer(data=flow, many=True, context={'request': request})
        serializer.is_valid()
        return Response(serializer.data)

    @action(detail=True, methods=['put'], url_path='check-profile')
    def check_profile(self, request, pk=None):
        ip = self.get_object()
        ptype = request.data.get("type")
        pip = get_object_or_404(ProfileIP, ip=ip, profile__profile_type=ptype)

        if not pip.LockedBy:
            pip.included = request.data.get('checked', not pip.included)
            pip.save()

        return Response()

    @permission_required_or_403('ip.add_informationpackage')
    def create(self, request, *args, **kwargs):
        """
        Prepares a new information package (IP) using the following tasks:
        1. Creates a new IP in the database.
        2. Creates a directory in the prepare directory with the name set to
        the id of the new IP.
        3. Creates an event in the database connected to the IP and with the
        detail "Prepare IP".
        Args:
        Returns:
            None
        """

        self.check_permissions(request)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        object_identifier_value = data['object_identifier_value']
        responsible = self.request.user

        if responsible.user_profile.current_organization is None:
            raise exceptions.ParseError('You must be part of an organization to prepare an IP')

        if data['package_type'] == InformationPackage.SIP:
            prepare_path = Path.objects.get(entity="preingest").value
        else:
            prepare_path = Path.objects.get(entity="disseminations").value

        if object_identifier_value:
            ip_exists = InformationPackage.objects.filter(object_identifier_value=object_identifier_value).exists()
            if ip_exists:
                raise Conflict('IP with object identifer value "%s" already exists' % object_identifier_value)

            if os.path.exists(os.path.join(prepare_path, object_identifier_value)):
                raise Conflict('IP with identifier "%s" already exists on disk' % object_identifier_value)

        perms = copy.deepcopy(getattr(settings, 'IP_CREATION_PERMS_MAP', {}))
        try:
            with transaction.atomic():
                ip = InformationPackage.objects.create(
                    object_identifier_value=object_identifier_value,
                    label=data['label'],
                    package_type=data['package_type'],
                    responsible=responsible,
                    state="Preparing",
                )
                ip.entry_date = ip.create_date

                if ip.package_type == InformationPackage.DIP:
                    ip.orders.add(*data['orders'])

                extra = {
                    'event_type': 10100,
                    'object': str(ip.pk),
                    'agent': request.user.username,
                    'outcome': EventIP.SUCCESS
                }
                self.logger.info("Prepared IP ({obj})".format(obj=ip.object_identifier_value), extra=extra)

                member = Member.objects.get(django_user=responsible)
                user_perms = perms.pop('owner', [])
                organization = member.django_user.user_profile.current_organization
                organization.assign_object(ip, custom_permissions=perms)
                organization.add_object(ip)

                for perm in user_perms:
                    perm_name = get_permission_name(perm, ip)
                    assign_perm(perm_name, member.django_user, ip)

                obj_path = normalize_path(os.path.join(prepare_path, ip.object_identifier_value))
                os.mkdir(obj_path)
                ip.object_path = obj_path
                ip.save()
                extra = {
                    'event_type': 10200,
                    'object': str(ip.pk),
                    'agent': request.user.username,
                    'outcome': EventIP.SUCCESS
                }
                self.logger.info("Created IP root directory", extra=extra)
        except IntegrityError:
            try:
                shutil.rmtree(obj_path)
            except OSError:
                pass
            raise

        return Response({"detail": "Prepared IP"}, status=status.HTTP_201_CREATED)

    @transaction.atomic
    @permission_required_or_403('ip.prepare_ip')
    @action(detail=True, methods=['post'], url_path='prepare')
    def prepare(self, request, pk=None):
        ip = self.get_object()
        sa = ip.submission_agreement

        if ip.state != 'Preparing':
            raise exceptions.ParseError('IP must be in state "Preparing"')

        if sa is None or not ip.submission_agreement_locked:
            raise exceptions.ParseError('IP requires locked SA to be prepared')

        if ip.package_type == InformationPackage.SIP:
            if not ProfileIP.objects.filter(ip=ip, profile=sa.profile_sip).exists():
                raise exceptions.ParseError('Information package missing SIP profile')

            if not ProfileIP.objects.filter(ip=ip, profile=sa.profile_submit_description).exists():
                raise exceptions.ParseError('Information package missing Submit Description profile')

        elif ip.package_type == InformationPackage.DIP:
            if not ProfileIP.objects.filter(ip=ip, profile=sa.profile_dip).exists():
                raise exceptions.ParseError('Information package missing DIP profile')

        if not ProfileIP.objects.filter(ip=ip, profile=sa.profile_transfer_project).exists():
            raise exceptions.ParseError('Information package missing Transfer Project profile')

        for profile_ip in ProfileIP.objects.select_for_update().filter(ip=ip).iterator(chunk_size=1000):
            try:
                if profile_ip:
                    profile_ip.clean()
                    profile_ip.lock(request.user)
            except ValidationError as e:
                logging.error('Validation error for profile %s: %s', profile_ip.profile.name, str(e))
                raise exceptions.ParseError('An error occurred while processing the profile_ip.')

        submit_description_data = ip.get_profile_data('submit_description')
        ip.start_date = submit_description_data.get('start_date')
        ip.end_date = submit_description_data.get('end_date')
        ip.save(update_fields=['start_date', 'end_date'])

        ProcessTask.objects.create(
            name="ESSArch_Core.ip.tasks.CreatePhysicalModel",
            label="Create Physical Model",
            eager=False,
            information_package=ip,
            responsible=self.request.user,
        ).run()

        return Response()

    @action(detail=True, methods=['get', 'post'], url_path='upload', permission_classes=[CanUpload])
    def upload(self, request, pk=None):
        ip = self.get_object()
        if ip.state not in ['Prepared', 'Uploading']:
            raise exceptions.ParseError('IP must be in state "Prepared" or "Uploading"')

        if ip.package_type == 'SIP':
            ip.state = "Uploading"
            ip.save(update_fields=['state'])

        data = request.GET if request.method == 'GET' else request.data

        dst = data.get('destination', '').strip('/ ')
        path = os.path.join(dst, data.get('flowRelativePath', ''))
        chunk_nr = data.get('flowChunkNumber')
        chunk_path = "%s_%s" % (path, chunk_nr)

        temp_path = os.path.join(Path.objects.get(entity='temp').value, 'file_upload')
        full_chunk_path = os.path.join(temp_path, str(ip.pk), chunk_path)

        if request.method == 'GET':
            if os.path.exists(full_chunk_path):
                chunk_size = int(data.get('flowChunkSize'))
                if os.path.getsize(full_chunk_path) != chunk_size:
                    return Response(status=status.HTTP_400_BAD_REQUEST)
                return Response(status=status.HTTP_200_OK)

            return Response(status=status.HTTP_204_NO_CONTENT)

        if request.method == 'POST':
            chunk = request.FILES['file']
            os.makedirs(os.path.dirname(full_chunk_path), exist_ok=True)

            with open(full_chunk_path, 'wb+') as chunkf:
                for c in chunk.chunks():
                    chunkf.write(c)

            return Response("Uploaded chunk", status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='merge-uploaded-chunks', permission_classes=[CanUpload])
    def merge_uploaded_chunks(self, request, pk=None):
        ip = self.get_object()
        if ip.package_type == 'SIP' and ip.state != 'Uploading':
            raise exceptions.ParseError('IP must be in state "Uploading"')

        temp_path = os.path.join(Path.objects.get(entity='temp').value, 'file_upload')
        chunks_path = os.path.join(temp_path, str(ip.pk), request.data['path'])
        filepath = os.path.join(ip.object_path, request.data['path'])

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        try:
            merge_file_chunks(chunks_path, filepath)
        except NoFileChunksFound:
            raise exceptions.NotFound('No chunks found')

        logger = logging.getLogger('essarch')
        logger.info("Uploaded %s" % filepath)

        return Response("Merged chunks")

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='set-uploaded', permission_classes=[CanSetUploaded])
    def set_uploaded(self, request, pk=None):
        ip = self.get_object()
        if ip.state not in ['Prepared', 'Uploading']:
            raise exceptions.ParseError('IP must be in state "Prepared" or "Uploading"')

        # delete temp files
        try:
            temp_path = os.path.join(Path.objects.get(entity='temp').value, 'file_upload', str(ip.pk))
            shutil.rmtree(temp_path)
        except FileNotFoundError:
            pass

        ProcessTask.objects.create(
            name="ESSArch_Core.tasks.UpdateIPSizeAndCount",
            label="Update IP size and file count",
            args=["Uploaded"],
            eager=False,
            information_package=ip,
            responsible=self.request.user
        ).run()

        return Response()

    @action(detail=True, methods=['post'], url_path='actiontool')
    def actiontool(self, request, pk=None):
        ip = self.get_object()
        if ip.state not in ['Prepared', 'Uploading', 'Received']:
            raise exceptions.ParseError('IP must be in state "Prepared", "Uploading" or "Received"')

        serializer = ActionToolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        workflow_spec = []

        for action_data in serializer.validated_data['actions']:
            tool_name = action_data['name']

            # ensure that tool exists
            action_tool = ActionTool.objects.get(name=tool_name)

            options = action_data['options']
            pattern = None

            if 'path' in action_data:
                pattern = action_data['path']

            if action_tool.environment == "task":
                tool_cmd = json.loads(action_tool.cmd)
                tool_cmd.update(options)
                workflow_spec.append({
                    "name": action_tool.path,
                    "label": tool_name,
                    "params": tool_cmd
                })
            else:
                workflow_spec.append({
                    "name":
                    "ESSArch_Core.fixity.action.tasks.Action",
                    "label":
                    tool_name,
                    "args": [
                        tool_name, pattern, ip.object_path, options,
                        request.data.get('purpose')
                    ]
                })

        workflow = create_workflow(workflow_spec, eager=False, ip=ip, name='Action tool')
        workflow.run()

        return Response()

    @action(detail=True, methods=['post'], url_path='actiontool_save_as')
    def save_actiontool(self, request, pk=None):
        ip = self.get_object()
        if ip.state not in ['Prepared', 'Uploaded', 'Created', 'At reception', 'Received', 'Preserved',
                            'Access Workarea']:
            # if ip.state not in ['Access Workarea']:
            raise exceptions.ParseError('IP must be in state "Prepared", "Uploaded", "Created", "At reception",\
                                        "Received", "Preserved" or "Access Workarea"')
            # 'IP must be in state "Access Workarea"')

        serializer = ActionToolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversions = None

        workflow_spec = [{"step": True, "name": "Action tool", "children": []}]

        for action_data in serializer.validated_data['actions']:
            tool_name = action_data['name']

            ActionTool.objects.get(name=tool_name)

            options = action_data['options']
            pattern = None

            if 'path' in action_data:
                pattern = action_data['path']
            if 'conversions' in action_data:
                conversions = action_data['conversions']

            workflow_spec[0]['children'].append({
                "name":
                "ESSArch_Core.fixity.action.tasks.Action",
                "label":
                tool_name,
                "args":
                [tool_name, pattern, options, conversions,
                 request.data.get('purpose')]
            })

        # Save action workflow profile
        action_workflow_name = request.data.get('action_workflow_name')
        action_workflow_status = request.data.get('action_workflow_status')
        dct = {
            'name': action_workflow_name,
            'profile_type': 'action_workflow',
            'type': 'Action Workflow',
            'status': action_workflow_status,
            'label': action_workflow_name,
            'specification': workflow_spec,
        }

        Profile.objects.update_or_create(name=dct['name'], defaults=dct)

        return Response()

    @action(detail=True, methods=['put'], url_path='actiontool_save')
    def save_actiontool_copy(self, request, pk=None):
        ip = self.get_object()
        if ip.state not in ['Prepared', 'Uploaded', 'Created', 'At reception', 'Received', 'Preserved',
                            'Access Workarea']:
            # if ip.state not in ['Access Workarea']:
            raise exceptions.ParseError(
                'IP must be in state "Prepared", "Uploaded", "Created", "At reception", "Received", \
"Preserved" or "Access Workarea"')
            # 'IP must be in state "Access Workarea"')

        serializer = ActionToolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        workflow_spec = [{"step": True, "name": "Action tool", "children": []}]

        for action_data in serializer.validated_data['actions']:
            tool_name = action_data['name']

            # ensure that tool exists
            ActionTool.objects.get(name=tool_name)

            options = action_data['options']
            pattern = None

            if 'path' in action_data:
                pattern = action_data['path']
            if 'conversions' in action_data:
                conversions = action_data['conversions']

            workflow_spec[0]['children'].append({
                "name":
                "ESSArch_Core.fixity.action.tasks.Action",
                "label":
                tool_name,
                "args":
                [tool_name, pattern, options, conversions,
                 request.data.get('purpose')]
            })

        # Save action workflow profile
        action_workflow_name = request.data.get('action_workflow_name')
        action_workflow_status = request.data.get('action_workflow_status')
        dct = {
            'name': action_workflow_name,
            'profile_type': 'action_workflow',
            'type': 'Action Workflow',
            'status': action_workflow_status,
            'label': action_workflow_name,
            'specification': workflow_spec,
        }
        try:
            obj = Profile.objects.get(name=dct['name'])
            obj.field = dct
            obj.save(update_fields=['field'])
        except Profile.DoesNotExist:
            obj = Profile.objects.create(field=dct)

        return Response()

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='create', permission_classes=[CanCreateSIP])
    def create_ip(self, request, pk=None):
        """
        Creates the specified information package
        Args:
            pk: The primary key (id) of the information package to create
        Returns:
            None
        """

        ip = self.get_object()

        if ip.state != "Uploaded":
            raise exceptions.ParseError("The IP (%s) is in the state '%s' but should be 'Uploaded'" % (pk, ip.state))

        ip.state = 'Creating'
        ip.save(update_fields=['state'])

        generate_premis = ip.profile_locked('preservation_metadata')

        convert_files = request.data.get('file_conversion', False)
        file_format_map = {
            'doc': 'pdf',
            'docx': 'pdf'
        }

        validators = request.data.get('validators', {})
        validate_xml_file = validators.get('validate_xml_file', True)
        validate_logical_physical_representation = validators.get('validate_logical_physical_representation', True)
        cts = ip.get_content_type_file()
        has_cts = cts is not None and os.path.exists(cts)
        has_representations = find_destination("representations", ip.get_structure(), ip.object_path)[1] is not None

        dst_dir = Path.objects.cached('entity', 'preingest', 'value')
        dst_filename = ip.object_identifier_value + '.' + ip.get_container_format().lower()
        dst = os.path.join(dst_dir, dst_filename)

        workflow_spec = [
            {
                "name": "ESSArch_Core.tasks.ConvertFile",
                "if": convert_files,
                "label": "Convert Files",
                "args": ["{{_OBJPATH}}", file_format_map]
            },
            {
                "name": "ESSArch_Core.ip.tasks.DownloadSchemas",
                "label": "Download Schemas",
            },
            {
                "step": True,
                "name": "Create Log File",
                "children": [
                    {
                        "name": "ESSArch_Core.ip.tasks.GenerateEventsXML",
                        "label": "Generate events xml file",
                    },
                    {
                        "name": "ESSArch_Core.tasks.AppendEvents",
                        "label": "Add events to xml file",
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.AddPremisIPObjectElementToEventsFile",
                        "label": "Add premis IP object to xml file",
                    },

                ]
            },
            {
                "name": "ESSArch_Core.ip.tasks.GenerateContentMetadata",
                "label": "Generate contentmetadata",
            },
            {
                "step": True,
                "name": "Validation",
                "if": any([validate_xml_file, validate_logical_physical_representation]),
                "children": [
                    {
                        "name": "ESSArch_Core.tasks.ValidateXMLFile",
                        "if": validate_xml_file,
                        "label": "Validate content-mets",
                        "params": {
                            "xml_filename": "{{_CONTENT_METS_PATH}}",
                        }
                    },
                    {
                        "name": "ESSArch_Core.tasks.ValidateXMLFile",
                        "if": generate_premis and validate_xml_file,
                        "label": "Validate premis",
                        "params": {
                            "xml_filename": "{{_PREMIS_PATH}}",
                        }
                    },
                    {
                        "name": "ESSArch_Core.tasks.ValidateXMLFile",
                        "label": "Validate cts",
                        "if": has_cts and validate_xml_file,
                        "run_if": "{{_CTS_PATH | path_exists}}",
                        "params": {
                            "xml_filename": "{{_CTS_PATH}}",
                            "schema_filename": "{{_CTS_SCHEMA_PATH}}",
                        }
                    },
                    {
                        "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                        "if": validate_logical_physical_representation,
                        "label": "Redundancy check against content-mets",
                        "args": ["{{_OBJPATH}}", "{{_CONTENT_METS_PATH}}"],
                    },
                    {
                        "name": "ESSArch_Core.tasks.CompareXMLFiles",
                        "if": generate_premis,
                        "label": "Compare premis and content-mets",
                        "args": ["{{_PREMIS_PATH}}", "{{_CONTENT_METS_PATH}}"],
                        "params": {'recursive': False},
                    },
                    {
                        "name": "ESSArch_Core.tasks.CompareRepresentationXMLFiles",
                        "if": has_representations and generate_premis,
                        "label": "Compare representation premis and mets",
                    }
                ]
            },
            {
                "name": "ESSArch_Core.ip.tasks.CreateContainer",
                "label": "Create container",
                "args": [ip.object_path, dst]
            },
            {
                "name": "ESSArch_Core.tasks.UpdateIPPath",
                "label": "Update IP path",
                "args": [dst]
            },
            {
                "name": "ESSArch_Core.tasks.DeleteFiles",
                "label": "Delete IP directory",
                "log": {},
                "args": [ip.object_path]
            },
            {
                "name": "ESSArch_Core.tasks.UpdateIPStatus",
                "label": "Set status to created SIP",
                "log": {
                    "event_type": "10400",
                    "outcome": "SUCCESS",
                    "msg": "Created SIP ({})".format(ip.object_identifier_value),
                },
                "args": ["Created"],
            },
        ]
        workflow = create_workflow(workflow_spec, ip, name="Create SIP")
        workflow.run()
        return Response({'status': 'creating ip'})

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='submit', permission_classes=[CanSubmitSIP])
    def submit(self, request, pk=None):
        """
        Submits the specified information package
        Args:
            pk: The primary key (id) of the information package to submit
        Returns:
            None
        """

        ip = self.get_object()

        if ip.state != "Created":
            return Response(
                "The IP (%s) is in the state '%s' but should be 'Created'" % (pk, ip.state),
                status=status.HTTP_400_BAD_REQUEST
            )

        ip.state = 'Submitting'
        ip.save(update_fields=['state'])

        sd_profile = ip.get_profile('submit_description')

        if sd_profile is None:
            return Response(
                "The IP (%s) has no submit description profile" % pk,
                status=status.HTTP_400_BAD_REQUEST
            )

        recipient = ip.get_email_recipient()

        validators = request.data.get('validators', {})
        validate_xml_file = validators.get('validate_xml_file', False)
        validate_logical_physical_representation = validators.get('validate_logical_physical_representation', False)

        workflow_spec = [
            {
                "name": "ESSArch_Core.ip.tasks.GeneratePackageMets",
                "label": "Generate package-mets",
            },
            {
                "name": "ESSArch_Core.tasks.ValidateXMLFile",
                "if": validate_xml_file,
                "label": "Validate package-mets",
                "params": {
                    "xml_filename": "{{_PACKAGE_METS_PATH}}",
                }
            },
            {
                "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                "if": validate_logical_physical_representation,
                "label": "Redundancy check against package-mets",
                "args": ["{{_OBJPATH}}", "{{_PACKAGE_METS_PATH}}"],
            },
            {
                "name": "ESSArch_Core.ip.tasks.SubmitSIP",
                "label": "Submit SIP",
            },
            {
                "name": "ESSArch_Core.tasks.UpdateIPStatus",
                "label": "Set status to submitted SIP",
                "log": {
                    "event_type": "10500",
                    "outcome": "SUCCESS",
                    "msg": "Submitted SIP ({})".format(ip.object_identifier_value),
                },
                "args": ["Submitted"],
            },
            {
                "name": "ESSArch_Core.tasks.SendEmail",
                "if": recipient,
                "label": "Send email",
                "params": {
                    "subject": "Submitted {{_OBJID}}",
                    "body": "{{_OBJID}} has been submitted",
                    "recipients": [recipient],
                    "attachments": [
                        "{{_PACKAGE_METS_PATH}}",
                    ],
                }
            },
        ]
        workflow = create_workflow(workflow_spec, ip, name="Submit SIP")
        workflow.run()
        return Response({'status': 'submitting ip'})

    @staticmethod
    def first_generation_case(lower_higher):
        return Case(
            When(aic__isnull=True, then=Value(True)),
            When(package_type=InformationPackage.AIC, then=Value(True)),
            When(generation=Subquery(lower_higher.values('min_gen')[:1]),
                 then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )

    @staticmethod
    def last_generation_case(lower_higher):
        return Case(
            When(aic__isnull=True, then=Value(True)),
            When(package_type=InformationPackage.AIC, then=Value(True)),
            When(generation=Subquery(lower_higher.values('max_gen')[:1]),
                 then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )

    def filter_queryset(self, queryset):
        return queryset

    def apply_filters(self, queryset):
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    def apply_ordering_filters(self, queryset):
        tmp_qs = queryset
        for backend in list(self.filter_backends):
            tmp_qs = backend().filter_queryset(self.request, tmp_qs, self)
        return queryset.order_by(*tmp_qs.query.order_by)

    def get_serializer_class(self):
        if self.action == 'create':
            return InformationPackageCreateSerializer

        if self.action in ['partial_update', 'update']:
            return InformationPackageUpdateSerializer

        if self.action == 'list':
            view_type = self.request.query_params.get('view_type', 'aic')
            if view_type == 'flat':
                return InformationPackageSerializer
            return NestedInformationPackageSerializer

        return InformationPackageDetailSerializer

#    def get_serializer_context(self):
#        context = super().get_serializer_context()
#        context['view'] = self
#
#        checker = ObjectPermissionChecker(self.request.user)
#        if hasattr(self, 'outer_queryset') and hasattr(self, 'inner_queryset'):
#            checker.prefetch_perms(self.outer_queryset.distinct() | self.inner_queryset.distinct())
#        else:
#            checker.prefetch_perms(self.queryset)
#
#        context['perm_checker'] = checker
#
#        return context

    @action(detail=False, methods=['get'], url_path='get-xsds')
    def get_xsds(self, request, pk=None):
        static_path = os.path.join(settings.BASE_DIR, 'static/edead/xsds')
        filename_list = os.listdir(static_path)
        return Response(filename_list)

    @transaction.atomic
    @action(detail=False, methods=['post'], url_path='add-from-master')
    def add_from_master(self, request, pk=None):
        items = request.data
        if isinstance(items, list):
            serializer = InformationPackageFromMasterSerializer(instance='', data=items,
                                                                context={'request': request},
                                                                many=True)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            serializer = InformationPackageFromMasterSerializer(
                data=request.data, context={'request': request},
            )
            serializer.is_valid(raise_exception=True)
            ip = serializer.save()
            return Response(reverse('informationpackage-detail', args=(ip.pk,)))

    @action(detail=False, methods=['post'], url_path='add-file-from-master')
    def add_file_from_master(self, request, pk=None):
        temp_dir = Path.objects.get(entity='temp').value
        dst = request.data.get('dst') or temp_dir

        if not request.user.has_perm('ip.can_receive_remote_files'):
            raise exceptions.PermissionDenied

        f = request.FILES['file']
        content_range = request.META.get('HTTP_CONTENT_RANGE', 'bytes 0-0/0')
        filename = os.path.join(dst, f.name)

        (start, end, total) = parse_content_range_header(content_range)

        if f.size != end - start + 1:
            raise exceptions.ParseError("File size doesn't match headers")

        if start == 0:
            with open(filename, 'wb') as dstf:
                dstf.write(f.read())
        else:
            with open(filename, 'ab') as dstf:
                dstf.seek(start)
                dstf.write(f.read())

        upload_id = request.data.get('upload_id', uuid.uuid4().hex)
        return Response({'upload_id': upload_id})

    @action(detail=False, methods=['post'], url_path='add-file-from-master_complete')
    def add_file_from_master_complete(self, request, pk=None):
        temp_dir = Path.objects.get(entity='temp').value
        dst = request.data.get('dst') or temp_dir

        if not request.user.has_perm('ip.can_receive_remote_files'):
            raise exceptions.PermissionDenied

        md5 = request.data['md5']
        filepath = request.data['path']
        filepath = os.path.join(dst, filepath)

        options = {'expected': md5, 'algorithm': 'md5'}
        validator = ChecksumValidator(context='checksum_str', options=options)
        validator.validate(filepath)

        return Response('Upload of %s complete' % filepath)

    @transaction.atomic
    def destroy(self, request, pk=None):
        ip = self.get_object()

        if not request.user.has_perm('delete_informationpackage', ip):
            raise exceptions.PermissionDenied('You do not have permission to delete this IP')

        self.logger.info(
            'Request issued to delete %s %s' % (ip.get_package_type_display(), pk),
            extra={'user': request.user.pk}
        )

        if ip.package_type == InformationPackage.AIC:
            raise exceptions.ParseError(detail='AICs cannot be deleted')

        if ip.package_type == InformationPackage.AIP:
            if ip.is_first_generation():
                if not request.user.has_perm('ip.delete_first_generation'):
                    raise exceptions.PermissionDenied(
                        'You do not have permission to delete the first generation of an IP'
                    )

            if ip.is_last_generation():
                if not request.user.has_perm('ip.delete_last_generation'):
                    raise exceptions.PermissionDenied(
                        'You do not have permission to delete the last generation of an IP'
                    )

        if ip.archived:
            if not request.user.has_perm('delete_archived', ip):
                raise exceptions.PermissionDenied('You do not have permission to delete archived IPs')

        t = ProcessTask.objects.create(
            name='ESSArch_Core.ip.tasks.DeleteInformationPackage',
            params={
                'from_db': True,
                'delete_files': request.query_params.get('delete_files', True)
            },
            eager=False,
            information_package=ip,
            responsible=request.user,
        )
        t.run()
        return Response({"detail": "Deleting information package", "task": t.pk}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['get', 'post'], url_path='ead-editor')
    def ead_editor(self, request, pk=None):
        ip = self.get_object()
        try:
            structure = ip.get_profile('sip').structure
        except AttributeError:
            return Response("No SIP profile for IP created yet", status=status.HTTP_400_BAD_REQUEST)

        ead_dir, ead_name = find_destination("archival_description_file", structure)

        if ead_name is None:
            return Response("No EAD file for IP found", status=status.HTTP_404_NOT_FOUND)

        xmlfile = os.path.join(ip.object_path, ead_dir, ead_name)

        if request.method == 'GET':

            try:
                with open(xmlfile) as f:
                    s = f.read()
                    return Response({"data": s})
            except IOError:
                open(xmlfile, 'a').close()
                return Response({"data": ""})

        content = request.POST.get("content", '')

        with open(xmlfile, "w") as f:
            f.write(str(content))
            return Response("Content written to %s" % xmlfile)

    @transaction.atomic
    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        logger = logging.getLogger('essarch.ingest')

        ip = self.get_object()
        workarea = ip.workareas.filter(read_only=False).first()

        if workarea is None:
            raise exceptions.ParseError(detail='IP not in writeable workarea')

        workflow = [
            {
                "name": "ESSArch_Core.workflow.tasks.ReceiveAIP",
                "label": "Receive IP",
                "args": [str(workarea.pk)],
            },
            {
                "name": "ESSArch_Core.ip.tasks.DeleteWorkarea",
                "label": "Delete from workspace",
                "args": [str(workarea.pk)],
            },
            {
                "name": "ESSArch_Core.tasks.UpdateIPSizeAndCount",
                "label": "Update IP size and file count",
            },
            {
                "name": "ESSArch_Core.tasks.UpdateIPStatus",
                "label": "Set status to received",
                "args": ["Received"],
            },
        ]
        workflow = create_workflow(workflow, ip, name='Receive from workspace')
        workflow.run()
        logger.info(
            'Started receiving {objid} from workspace'.format(objid=ip.object_identifier_value),
            extra={'user': request.user.pk},
        )
        return Response({'detail': gettext('Receiving {ip}').format(ip=ip)})

    @action(detail=True, methods=['post'], url_path='preserve')
    def preserve(self, request, pk=None):
        with transaction.atomic():
            ip = self.get_object()

            if ip.package_type != InformationPackage.AIP:
                raise exceptions.ParseError('IP must be an AIP')
            if ip.archived:
                raise exceptions.ParseError('IP already preserved')
            if ip.state == "Preserving":
                raise exceptions.ParseError('IP already being preserved')

            reception_dir = Path.objects.get(entity='ingest_reception').value
            ingest_dir = getattr(ip.policy.ingest_path, 'value', None)
            ip_reception_path = os.path.join(reception_dir, ip.object_identifier_value)
            ip_ingest_path = os.path.join(ingest_dir, ip.object_identifier_value) if ingest_dir else None

            ip.state = "Preserving"
            ip.appraisal_date = request.data.get('appraisal_date', None)
            ip.save(update_fields=['state', 'appraisal_date'])

            archive = request.data.get('archive', None)

            for profile_ip in ProfileIP.objects.select_for_update().filter(ip=ip).iterator(chunk_size=1000):
                try:
                    profile_ip.clean()
                    profile_ip.lock(request.user)
                except ValidationError as e:
                    raise exceptions.ParseError('%s: %s' % (profile_ip.profile.name, str(e)))

            try:
                workarea_id = ip.workareas.get(read_only=False).pk
            except Workarea.DoesNotExist:
                workarea_id = None

            generate_premis = ip.profile_locked('preservation_metadata')
            has_representations = find_destination(
                "representations", ip.get_structure(), ip.object_path,
            )[1] is not None

            # remove existing premis and mets paths:
            mets_path = os.path.join(ip.object_path, ip.get_content_mets_file_path())
            try:
                os.remove(mets_path)
            except FileNotFoundError:
                pass

            ip.update_sip_data()

            if generate_premis:
                premis_profile_data = ip.get_profile_data('preservation_metadata')
                data = fill_specification_data(premis_profile_data, ip=ip)
                premis_path = parseContent(ip.get_premis_file_path(), data)
                full_premis_path = os.path.join(ip.object_path, premis_path)
                try:
                    os.remove(full_premis_path)
                except FileNotFoundError:
                    pass

            workflow = [
                {
                    "step": True,
                    "name": "Generate AIP",
                    "children": [
                        {
                            "name": "ESSArch_Core.ip.tasks.DownloadSchemas",
                            "label": "Download Schemas",
                        },
                        {
                            "step": True,
                            "name": "Create Log File",
                            "children": [
                                {
                                    "name": "ESSArch_Core.ip.tasks.GenerateEventsXML",
                                    "label": "Generate events xml file",
                                },
                                {
                                    "name": "ESSArch_Core.tasks.AppendEvents",
                                    "label": "Add events to xml file",
                                },
                                {
                                    "name": "ESSArch_Core.ip.tasks.AddPremisIPObjectElementToEventsFile",
                                    "label": "Add premis IP object to xml file",
                                },

                            ]
                        },
                        {
                            "name": "ESSArch_Core.ip.tasks.GenerateContentMetadata",
                            "label": "Generate contentmetadata",
                        },
                    ]
                },
                {
                    "step": True,
                    "name": "Validate AIP",
                    "children": [
                        {
                            "name": "ESSArch_Core.tasks.ValidateXMLFile",
                            "label": "Validate content-mets",
                            "params": {
                                "xml_filename": "{{_CONTENT_METS_PATH}}",
                            }
                        },
                        {
                            "name": "ESSArch_Core.tasks.ValidateXMLFile",
                            "if": generate_premis,
                            "label": "Validate premis",
                            "params": {
                                "xml_filename": "{{_PREMIS_PATH}}",
                            }
                        },
                        {
                            "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                            "label": "Redundancy check against content-mets",
                            "args": ["{{_OBJPATH}}", "{{_CONTENT_METS_PATH}}"],
                        },
                        {
                            "name": "ESSArch_Core.tasks.CompareXMLFiles",
                            "if": generate_premis,
                            "label": "Compare premis and content-mets",
                            "args": ["{{_PREMIS_PATH}}", "{{_CONTENT_METS_PATH}}"],
                            "params": {'recursive': False},
                        },
                        {
                            "name": "ESSArch_Core.tasks.CompareRepresentationXMLFiles",
                            "if": has_representations and generate_premis,
                            "label": "Compare representation premis and mets",
                        }
                    ]
                },
                {
                    "name": "ESSArch_Core.tasks.UpdateIPSizeAndCount",
                    "label": "Update IP size and file count",
                },
                {
                    "name": "ESSArch_Core.tasks.AddEvent",
                    "label": "Set status to created AIP",
                    "params": {
                        "event_type": "30200",
                        "outcome": "SUCCESS",
                        "msg": "Created AIP ({})".format(ip.object_identifier_value),
                    }
                },
            ]
            workflow += ip.create_preservation_workflow()
            workflow += [
                {
                    "name": "ESSArch_Core.ip.tasks.InsertArchivalDescription",
                    "label": "Update archival description",
                    "if": archive,
                    "args": [request.data]
                },
                {
                    "name": "ESSArch_Core.ip.tasks.CreateReceipt",
                    "label": "Create receipt",
                    "args": [
                        None,
                        "xml",
                        "receipts/xml.json",
                        "{{PATH_RECEIPTS}}/xml/{{_OBJID}}_{% now 'ymdHis' %}.xml",
                        "success",
                        gettext("Preserved {{OBJID}}"),
                        gettext("{{OBJLABEL}} ({{OBJID}}) is now preserved"),
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.Notify",
                    "label": "Notify responsible user",
                    "args": [
                        gettext("{ip} is now preserved").format(ip=ip),
                        logging.INFO,
                        True,
                    ],
                },
                {
                    "name": "ESSArch_Core.tasks.DeleteFiles",
                    "label": "Delete from reception",
                    "args": [ip_reception_path]
                },
                {
                    "name": "ESSArch_Core.tasks.DeleteFiles",
                    "label": "Delete from ingest",
                    "log": {},
                    "if": ip_ingest_path,
                    "args": [ip_ingest_path]
                },
                {
                    "name": "ESSArch_Core.ip.tasks.DeleteWorkarea",
                    "label": "Delete from workarea",
                    "if": workarea_id,
                    "args": [str(workarea_id)],
                },
            ]
            workflow = create_workflow(workflow, ip, name='Preserve Information Package')
        workflow.run()
        return Response({'detail': gettext('Preserving {ip}...').format(ip=ip), 'step': workflow.pk})

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='create_new_generation')
    def create_new_generation(self, request, pk=None):
        ip = self.get_object()
        workarea = ip.workareas.get()
        data = request.data
        new_object_identifier_value = data.get('object_identifier_value') or str(uuid.uuid4())
        access_workarea = Path.objects.get(entity='access_workarea').value
        access_workarea_user = os.path.join(access_workarea, request.user.username, new_object_identifier_value)
        access_workarea_user_extracted = os.path.join(access_workarea_user, new_object_identifier_value)
        new_aip = ip.create_new_generation('Access Workarea', request.user, new_object_identifier_value)
        new_aip.object_path = access_workarea_user_extracted
        new_aip.save()

        os.makedirs(access_workarea_user, exist_ok=True)
        for f in os.listdir(workarea.path):
            src_path = os.path.join(workarea.path, f)
            if os.path.isdir(src_path) and f == ip.object_identifier_value:
                dst_path = os.path.join(access_workarea_user, new_aip.object_identifier_value)
            else:
                dst_path = os.path.join(access_workarea_user, f)
            shutil.move(src_path, dst_path)

        os.removedirs(workarea.path)
        workarea.ip = new_aip
        workarea.read_only = False
        workarea.save()
        return Response({'detail': gettext('New generation created {ip}').format(ip=new_aip)})

    @transaction.atomic
    @action(detail=True, methods=['post'])
    def access(self, request, pk=None):
        ip = self.get_object()

        if ip.state != 'Received' and not ip.archived:
            raise exceptions.ParseError('IP must either have state "Received" or be archived to be accessed')

        data = request.data
        user = None
        if request and hasattr(request, "user"):
            user = request.user

        options = ['tar', 'extracted', 'edit']
        if ip.package_type == InformationPackage.AIP:
            options.append('new')

        if not any(x in options for x in data.keys()):
            raise exceptions.ParseError('No option set')

        if not any(v for k, v in data.items() if k in options):
            raise exceptions.ParseError('Need at least one option set to true')

        if data.get('extracted') and data.get('tar'):
            raise exceptions.ParseError('"extracted" and "tar" cannot both be true')

        if data.get('new'):
            if ip.package_type != InformationPackage.AIP:
                raise exceptions.ParseError('{} is not an AIP'.format(ip.object_identifier_value))

            if request.user.user_profile.current_organization is None:
                raise exceptions.ParseError('You must be part of an organization to create a new generation of an IP')

            if ip.archived and not request.user.has_perm('get_from_storage_as_new', ip):
                raise exceptions.PermissionDenied('You do not have permission to create new generations of this IP')

            if not ip.archived and not request.user.has_perm('add_to_ingest_workarea_as_new', ip):
                raise exceptions.PermissionDenied('You do not have permission to create new generations of this IP')

            if ip.new_version_in_progress() is not None:
                working_user = ip.new_version_in_progress().ip.responsible
                raise exceptions.ParseError(
                    'User %s already has a new generation in their workarea' % working_user.username
                )

            data['extracted'] = True

        workarea_type = Workarea.INGEST if ip.state == 'Received' else Workarea.ACCESS

        ip_workarea = ip.workareas.filter(user=request.user)
        ingest_path = Path.objects.get(entity='ingest_workarea')
        access_path = Path.objects.get(entity='access_workarea')

        ip_already_in_workarea = ip_workarea.exists() and (
            ip_workarea.filter(type=workarea_type).exists() or ingest_path == access_path
        )

        if not data.get('new') and ip_already_in_workarea:
            raise Conflict('IP already in workarea')

        workflow = ip.create_access_workflow(
            self.request.user,
            tar=data.get('tar', False),
            extracted=data.get('extracted', False),
            new=data.get('new', False),
            object_identifier_value=data.get('object_identifier_value'),
            package_xml=data.get('package_xml', False),
            aic_xml=data.get('aic_xml', False),
            diff_check=data.get('diff_check', False),
            edit=data.get('edit', False),
            responsible=user,
        )
        workflow.run()
        return Response({'detail': gettext('Accessing {ip}...').format(ip=ip), 'step': workflow.pk})

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='create-dip')
    def create_dip(self, request, pk=None):
        dip = InformationPackage.objects.get(pk=pk)

        if dip.package_type != InformationPackage.DIP:
            raise exceptions.ParseError('"%s" is not a DIP, it is a %s' % (dip, dip.package_type))

        if dip.state != 'Prepared':
            raise exceptions.ParseError('"%s" is not in the "Prepared" state' % dip)

        validators = request.data.get('validators', {})
        validate_xml_file = validators.get('validate_xml_file', True)
        validate_logical_physical_representation = validators.get('validate_logical_physical_representation', True)

        generate_premis = dip.profile_locked('preservation_metadata')
        has_representations = find_destination("representations", dip.get_structure(), dip.object_path)[1] is not None

        dst = os.path.join(
            os.path.dirname(dip.object_path),
            dip.object_identifier_value + '.' + dip.get_container_format().lower(),
        )

        order_path = Path.objects.get(entity='orders').value

        workflow_spec = [
            {
                "name": "ESSArch_Core.ip.tasks.DownloadSchemas",
                "label": "Download Schemas",
            },
            {
                "step": True,
                "name": "Create Log File",
                "children": [
                    {
                        "name": "ESSArch_Core.ip.tasks.GenerateEventsXML",
                        "label": "Generate events xml file",
                    },
                    {
                        "name": "ESSArch_Core.tasks.AppendEvents",
                        "label": "Add events to xml file",
                    },
                    {
                        "name": "ESSArch_Core.ip.tasks.AddPremisIPObjectElementToEventsFile",
                        "label": "Add premis IP object to xml file",
                    },

                ]
            },
            {
                "name": "ESSArch_Core.ip.tasks.GenerateContentMetadata",
                "label": "Generate contentmetadata",
            },
            {
                "step": True,
                "name": "Validation",
                "if": any([validate_xml_file, validate_logical_physical_representation]),
                "children": [
                    {
                        "name": "ESSArch_Core.tasks.ValidateXMLFile",
                        "if": validate_xml_file,
                        "label": "Validate content-mets",
                        "params": {
                            "xml_filename": "{{_CONTENT_METS_PATH}}",
                        }
                    },
                    {
                        "name": "ESSArch_Core.tasks.ValidateXMLFile",
                        "if": generate_premis and validate_xml_file,
                        "label": "Validate premis",
                        "params": {
                            "xml_filename": "{{_PREMIS_PATH}}",
                        }
                    },
                    {
                        "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                        "if": validate_logical_physical_representation,
                        "label": "Redundancy check against content-mets",
                        "args": ["{{_OBJPATH}}", "{{_CONTENT_METS_PATH}}"],
                    },
                    {
                        "name": "ESSArch_Core.tasks.CompareXMLFiles",
                        "if": generate_premis and validate_xml_file,
                        "label": "Compare premis and content-mets",
                        "args": ["{{_PREMIS_PATH}}", "{{_CONTENT_METS_PATH}}"],
                        "params": {'recursive': False},
                    },
                    {
                        "name": "ESSArch_Core.tasks.CompareRepresentationXMLFiles",
                        "if": has_representations and generate_premis,
                        "label": "Compare representation premis and mets",
                    }
                ]
            },
            {
                "name": "ESSArch_Core.ip.tasks.CreateContainer",
                "label": "Create container",
                "args": [dip.object_path, dst]
            },
            {
                "step": True,
                "name": "Add to orders",
                "if": dip.orders.exists(),
                "children": [
                    {
                        "name": "ESSArch_Core.tasks.CopyFile",
                        "label": "Add to order {}".format(order.label),
                        "args": [
                            dst,
                            os.path.join(order_path, str(order.pk), os.path.basename(dst)),
                        ]
                    } for order in dip.orders.all()
                ],
            },
            {
                "name": "ESSArch_Core.tasks.UpdateIPPath",
                "label": "Update IP path",
                "args": [dst]
            },
            {
                "name": "ESSArch_Core.tasks.DeleteFiles",
                "label": "Delete IP directory",
                "args": [dip.object_path]
            },
            {
                "name": "ESSArch_Core.tasks.UpdateIPStatus",
                "label": "Set status to created DIP",
                "log": {
                    "event_type": "30600",
                    "outcome": "SUCCESS",
                    "msg": "Created DIP ({})".format(dip.object_identifier_value),
                },
                "args": ["Created"],
            },
        ]

        dip.state = 'Creating'
        dip.save(update_fields=['state'])
        workflow = create_workflow(workflow_spec, dip, name="Create DIP")
        workflow.run()
        return Response({'status': 'creating dip'})

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        ip = self.get_object()
        path = ip.object_path
        if ip.package_type != InformationPackage.DIP:
            raise exceptions.ParseError('Cannot download IP of package type {}'.format(ip.get_package_type_display()))

        if ip.state != 'Created':
            raise exceptions.ParseError("Cannot download IP that is not in 'Created' state")

        fid = FormatIdentifier(allow_unknown_file_types=True)
        content_type = fid.get_mimetype(path)

        # Django closes the file automatically, therefore we
        # should not open the file using a context manager

        return generate_file_response(
            open(path, 'rb'),
            content_type=content_type,
            force_download=True,
            name=os.path.basename(path),
        )

    @action(detail=True, methods=['delete', 'get', 'post'], permission_classes=[IsResponsibleOrCanSeeAllFiles])
    def files(self, request, pk=None):
        ip = self.get_object()
        download = request.query_params.get('download', False)
        if download is not False:
            download = string_to_bool(download)
        expand_container = request.query_params.get('expand_container', False)
        if expand_container is not False:
            expand_container = string_to_bool(expand_container)
        path = request.query_params.get('path', '').rstrip('/')

        if ip.archived and settings.ELASTICSEARCH_CONNECTIONS['default']['hosts'][0]['host']:
            if request.method in ['DELETE', 'POST']:
                raise exceptions.ParseError('You cannot modify preserved content')
            # check if path exists
            path = request.query_params.get('path', '').rstrip('/')
            s = Search(index=['directory', 'document'])
            s = s.source(excludes=["attachment.content"])
            s = s.filter('term', **{'ip': str(ip.pk)})

            if path != '':
                dirname = os.path.dirname(path)
                basename = os.path.basename(path)
                q = ElasticQ('bool',
                             should=[ElasticQ('bool', must=[ElasticQ('term', **{'href': dirname}),
                                                            ElasticQ('term', **{'name.keyword': basename})]),
                                     ElasticQ('bool', must=[ElasticQ('term', **{'href': dirname}),
                                                            ElasticQ('match', filename=basename)])])

                s = s.query(q)
                hits = s.execute()

                try:
                    hit = hits[0]
                except IndexError:
                    if len(path.split('.tar/')) == 2:
                        tar_path, tar_subpath = path.split('.tar/')
                        tar_path += '.tar'

                        with tarfile.open(fileobj=ip.open_file(tar_path, 'rb')) as tar:
                            try:
                                f = io.BytesIO(tar.extractfile(tar_subpath).read())
                                fid = FormatIdentifier(allow_unknown_file_types=True)
                                content_type = fid.get_mimetype(tar_subpath)
                                return generate_file_response(
                                    f,
                                    content_type=content_type,
                                    force_download=download, name=tar_subpath)
                            except KeyError:
                                raise exceptions.NotFound

                    if len(path.split('.zip/')) == 2:
                        zip_path, zip_subpath = path.split('.zip/')
                        zip_path += '.zip'

                        with zipfile.ZipFile(ip.open_file(zip_path, 'rb')) as zipf:
                            try:
                                f = io.BytesIO(zipf.read(zip_subpath))
                                fid = FormatIdentifier(allow_unknown_file_types=True)
                                content_type = fid.get_mimetype(zip_subpath)
                                return generate_file_response(
                                    f,
                                    content_type=content_type,
                                    force_download=download, name=zip_subpath)
                            except KeyError:
                                raise exceptions.NotFound
                    raise exceptions.NotFound

                if hit.meta.index.startswith('document'):
                    if expand_container and (path.endswith('.tar') or path.endswith('.zip')):
                        entries = ip.list_files(fileobj=ip.open_file(path, 'rb'), expand_container=expand_container)
                        return Response(entries)

                    fid = FormatIdentifier(allow_unknown_file_types=True)
                    content_type = fid.get_mimetype(path)
                    return generate_file_response(
                        ip.open_file(path, 'rb'),
                        content_type=content_type,
                        force_download=download, name=path
                    )

            # a directory with the path exists, get the content of it
            s = Search(index=['directory', 'document'])
            s = s.filter('term', **{'ip': str(ip.pk)}).query('term', **{'href': path}).sort('name.keyword')

            if self.paginator is not None:
                # Paginate in search engine
                params = {key: value[0] for (key, value) in dict(request.query_params).items()}

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
                try:
                    max_results = int(
                        Index('document').get_settings()['document']['settings']['index'].get(
                            'max_result_window', DEFAULT_MAX_RESULT_WINDOW
                        )
                    )
                except KeyError:
                    max_results = DEFAULT_MAX_RESULT_WINDOW

                s = s[offset:offset + size]

            try:
                results = s.execute()
            except TransportError:
                if self.paginator is not None:
                    if offset + size > max_results:
                        raise exceptions.ParseError("Can't show more than {max} results".format(max=max_results))

                raise

            if self.paginator is not None:
                ceil = math.ceil(results.hits.total['value'] / size)
                ceil = 1 if ceil < 1 else ceil
                if results.hits.total['value'] > 0 and number > ceil:
                    raise exceptions.NotFound('Invalid page.')

            results_list = []
            for hit in results:
                if hit.meta.index.startswith('directory'):
                    d = {
                        'type': 'dir',
                        'name': hit.name,
                    }
                else:
                    d = {
                        'type': 'file',
                        'name': hit.name,
                        'modified': hit.modified,
                        'size': hit.size,
                    }

                results_list.append(d)

            if self.paginator is not None:
                return Response(results_list, headers={'Count': results.hits.total['value']})

            return Response(results_list)

        if request.method not in permissions.SAFE_METHODS:
            if ip.state not in ['Prepared', 'Uploading']:
                raise exceptions.ParseError(
                    "Cannot delete or add content of an IP that is not in 'Prepared' or 'Uploading' state"
                )

        if request.method == 'DELETE':
            try:
                path = request.data['path']
            except KeyError:
                raise exceptions.ParseError('Path parameter missing')

            root = ip.object_path
            fullpath = os.path.join(root, path)

            if not in_directory(fullpath, root):
                raise exceptions.ParseError('Illegal path %s' % path)

            try:
                shutil.rmtree(fullpath)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    raise exceptions.NotFound('Path does not exist')

                if e.errno != errno.ENOTDIR:
                    raise

                os.remove(fullpath)

            return Response(status=status.HTTP_204_NO_CONTENT)

        if request.method == 'POST':
            if ip.package_type not in [InformationPackage.DIP, InformationPackage.SIP]:
                raise exceptions.MethodNotAllowed(request.method)

            try:
                path = os.path.join(ip.object_path, request.data['path'])
            except KeyError:
                raise exceptions.ParseError('Path parameter missing')

            try:
                pathtype = request.data['type']
            except KeyError:
                raise exceptions.ParseError('Type parameter missing')

            root = ip.object_path
            fullpath = os.path.join(root, path)

            if not in_directory(fullpath, root):
                raise exceptions.ParseError('Illegal path %s' % fullpath)

            if pathtype == 'dir':
                try:
                    os.makedirs(fullpath)
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        raise exceptions.ParseError('Directory %s already exists' % path)

                    raise
            elif pathtype == 'file':
                open(fullpath, 'a').close()
            else:
                raise exceptions.ParseError('Type must be either "file" or "dir"')

            return Response(path, status=status.HTTP_201_CREATED)

        return ip.get_path_response(path, request, force_download=download, expand_container=expand_container,
                                    paginator=self.paginator)

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='unlock-profile', permission_classes=[CanUnlockProfile])
    def unlock_profile(self, request, pk=None):
        ip = self.get_object()

        if ip.state in ['Submitting', 'Submitted']:
            raise exceptions.ParseError('Cannot unlock profiles in an IP that is %s' % ip.state)

        try:
            ptype = request.data["type"]
        except KeyError:
            raise exceptions.ParseError('Missing type parameter')

        ip.unlock_profile(ptype)

        return Response({
            'detail': gettext('Unlocking profile with type "{type}" in IP "{ip}"').format(type=ptype, ip=ip)
        })

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='validate')
    def validate(self, request, pk=None):
        ip = self.get_object()

        prepare = Path.objects.get(entity="ingest_workarea").value
        xmlfile = os.path.join(prepare, "%s.xml" % pk)

        step = ProcessStep.objects.create(
            name="Validation",
            information_package=ip
        )

        step.add_tasks(
            ProcessTask.objects.create(
                name="ESSArch_Core.tasks.ValidateXMLFile",
                params={
                    "xml_filename": xmlfile
                },
                log=EventIP,
                information_package=ip,
                responsible=self.request.user,
            ),
            ProcessTask.objects.create(
                name="ESSArch_Core.tasks.ValidateFiles",
                params={
                    "mets_path": xmlfile,
                    "validate_fileformat": True,
                    "validate_integrity": True,
                },
                log=EventIP,
                processstep_pos=0,
                information_package=ip,
                responsible=self.request.user,
            )
        )

        step.run()

        return Response("Validating IP")

    def update(self, request, *args, **kwargs):
        ip = self.get_object()

        if any(field in request.data for field in ['submission_agreement', 'submission_agreement_data']):
            if ip.submission_agreement_locked:
                return Response("SA connected to IP is locked", status=status.HTTP_400_BAD_REQUEST)

        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(ip, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(ip, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            ip._prefetched_objects_cache = {}

        serializer = InformationPackageDetailSerializer(instance=ip)
        return Response(serializer.data)


class OrderTypeViewSet(viewsets.ModelViewSet):
    queryset = OrderType.objects.all()
    serializer_class = OrderTypeSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (filters.OrderingFilter, SearchFilter,)
    ordering_fields = ('name',)
    search_fields = ('name',)


class OrderViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows orders to be viewed or edited.
    """
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsOrderResponsibleOrAdmin]

    def get_queryset(self):
        if self.action == 'list':
            if self.request.user.is_superuser:
                return self.queryset

            return self.queryset.filter(responsible=self.request.user)

        return self.queryset

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'metadata']:
            return OrderWriteSerializer
        return self.serializer_class

    @action(detail=True, methods=['get'])
    def download(self, request, pk):
        order = self.get_object()

        zip_buffer = io.BytesIO()
        zip_directory(order.path, zip_buffer, arcroot=order.label)

        return generate_file_response(
            zip_buffer,
            content_type='application/zip',
            force_download=True,
            name='{}.zip'.format(order.label),
        )


class InformationPackageReceptionViewSet(viewsets.ViewSet, PaginatedViewMixin):
    search_fields = (
        'object_identifier_value', 'label', 'responsible__first_name',
        'responsible__last_name', 'responsible__username', 'state',
        'submission_agreement__name', 'start_date', 'end_date',
    )

    permission_classes = ()

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger('essarch.reception')
        self.reception = Path.objects.get(entity="ingest_reception").value
        self.uip = Path.objects.get(entity="ingest_unidentified").value
        super().__init__(*args, **kwargs)

    def find_xml_files(self, path):
        for xmlfile in glob.glob(os.path.join(path, "*.xml")):
            if os.path.isfile(xmlfile) and not xmlfile.endswith('_ipevents.xml'):
                yield xmlfile

    def get_container_for_xml(self, xmlfile):
        doc = etree.parse(xmlfile)
        root = doc.getroot()
        return get_objectpath(root)

    def get_contained_packages(self, path):
        ips = []

        for xmlfile in self.find_xml_files(path):
            try:
                container = os.path.join(path, self.get_container_for_xml(xmlfile))
            except etree.LxmlError:
                continue

            ip_id = os.path.splitext(os.path.basename(xmlfile))[0]
            existing_ips = InformationPackage.objects.filter(
                object_identifier_value=ip_id
            ).exclude(
                state="Submitted"
            )

            if existing_ips.exists():
                continue

            ip = parse_submit_description(xmlfile, srcdir=os.path.split(container)[0])

            ip['container'] = container
            ip['xml'] = xmlfile
            ip['type'] = 'contained'
            ip['state'] = 'At reception'
            ip['status'] = 100
            ip['step_state'] = celery_states.SUCCESS
            ips.append(ip)

        return ips

    def get_extracted_packages(self, path):
        ips = []

        for d in os.listdir(path):
            if not os.path.isdir(os.path.join(path, d)):
                continue

            if InformationPackage.objects.filter(object_identifier_value=d).exists():
                continue

            ip = {
                'id': d,
                'object_identifier_value': d,
                'type': 'extracted',
                'state': 'At reception',
                'status': 100,
                'step_state': celery_states.SUCCESS,
            }

            ips.append(ip)

        return ips

    def list(self, request):
        filterset_fields = [
            "label", "object_identifier_value", "responsible",
            "create_date", "object_size", "start_date", "end_date"
        ]

        reception = Path.objects.values_list('value', flat=True).get(entity='ingest_reception')

        contained = self.get_contained_packages(reception)
        extracted = self.get_extracted_packages(reception)
        ips = contained + extracted

        # Remove all keys not in filterset_fields
        conditions = {key: value for (key, value) in request.query_params.items() if key in filterset_fields}

        # Filter ips based on conditions
        new_ips = list(filter(lambda ip: all((v in str(ip.get(k)) for (k, v) in conditions.items())), ips))

        from_db = InformationPackage.objects.visible_to_user(request.user).filter(
            Q(
                Q(
                    package_type=InformationPackage.AIP,
                    state__in=['At reception', 'Receiving']
                ) |
                Q(
                    package_type=InformationPackage.SIP,
                    state__in=['Transferring', 'Transferred']
                )
            ),
            **conditions
        )
        serializer = InformationPackageSerializer(
            data=from_db, many=True, context={'request': request, 'view': self}
        )
        serializer.is_valid()

        # Remove IPs from new_ips if they already are in the database
        db_ip_ids = from_db.filter(
            object_identifier_value__in=[i['id'] for i in new_ips]
        ).values_list('object_identifier_value', flat=True)
        new_ips = [ip for ip in new_ips if ip['id'] not in db_ip_ids]

        new_ips.extend(serializer.data)

        if self.paginator is not None:
            paginated = self.paginator.paginate_queryset(new_ips, request)
            return self.paginator.get_paginated_response(paginated)

        return Response(new_ips)

    def retrieve(self, request, pk=None):
        path = Path.objects.values_list('value', flat=True).get(entity='ingest_reception')
        fullpath = os.path.join(path, "%s.xml" % pk)

        if not os.path.exists(fullpath):
            try:
                ip = InformationPackage.objects.get(
                    object_identifier_value=pk,
                    package_type=InformationPackage.AIP,
                    state='Receiving',
                )
                return Response(InformationPackageDetailSerializer(instance=ip).data)
            except InformationPackage.DoesNotExist:
                raise exceptions.NotFound

        return Response(parse_submit_description(fullpath, srcdir=path))

    def _prepare(self, request, pk):
        logger = logging.getLogger('essarch.ingest')
        perms = copy.deepcopy(getattr(settings, 'IP_CREATION_PERMS_MAP', {}))
        organization = request.user.user_profile.current_organization

        existing_non_sip = InformationPackage.objects.filter(
            object_identifier_value=pk,
        ).exclude(package_type=InformationPackage.SIP).first()
        existing_sip = InformationPackage.objects.filter(
            object_identifier_value=pk, package_type=InformationPackage.SIP
        ).first()

        if existing_non_sip is not None:
            logger.warning('Tried to receive IP with id %s which already exists' % pk, extra={'user': request.user.pk})
            raise Conflict('IP with id {} already exists'.format(pk))

        reception = Path.objects.values_list('value', flat=True).get(entity='ingest_reception')
        uip = Path.objects.get(entity="ingest_unidentified").value
        # This does not do anything particular right now
        # other than setting a nut null value for package_mets_path. Plausible use when an UIP is a proper SIP but SA
        # is not registred in the preservation system
        xmlfile = os.path.join(uip, "%s.xml" % pk)

        if os.path.isdir(os.path.join(reception, pk)):
            ip_is_directory = True
            # A directory with the given id exists, try to prepare it
            sa = request.data.get('submission_agreement')
            if sa is None:
                raise exceptions.ParseError(
                    detail='Missing parameter submission_agreement')
            sa = SubmissionAgreement.objects.select_for_update().get(pk=sa)
            parsed = {'label': pk}
            container = os.path.join(reception, pk)
            ip = InformationPackage.objects.create(
                object_identifier_value=pk,
                package_type=InformationPackage.SIP,
                state='Prepared',
                responsible=request.user,
                submission_agreement=sa,
                submission_agreement_locked=True,
                object_path=container,
                label=parsed.get('label'),
                package_mets_path=xmlfile,
            )
            user_perms = perms.pop('owner', [])
            member = Member.objects.get(django_user=request.user)
            for perm in user_perms:
                perm_name = get_permission_name(perm, ip)
                assign_perm(perm_name, member.django_user, ip)

            ProfileIP.objects.select_for_update().filter(ip=ip).delete()
            sa.lock_to_information_package(ip, request.user)
        else:
            xmlfile = normalize_path(os.path.join(reception, '%s.xml' % pk))
            ip_is_directory = False

            if not os.path.isfile(xmlfile):
                logger.warning('Tried to receive IP with missing XML file %s' %
                               xmlfile, extra={'user': request.user.pk})
                raise exceptions.NotFound('%s does not exist' % xmlfile)
            try:
                container = normalize_path(os.path.join(reception, self.get_container_for_xml(xmlfile)))
            except etree.LxmlError:
                logger.warning('Tried to receive IP with invalid XML file %s' %
                               xmlfile, extra={'user': request.user.pk})
                raise exceptions.ParseError('Invalid XML file, %s' % xmlfile)

            if not os.path.isfile(container):
                logger.warning(
                    'Tried to receive IP with missing container file %s' % container,
                    extra={'user': request.user.pk}
                )
                raise exceptions.NotFound('%s does not exist' % container)

            if existing_sip is None:
                if organization is None:
                    raise exceptions.ParseError('You must be part of an organization to receive IP')

                parsed = parse_submit_description(xmlfile, srcdir=os.path.dirname(container))
                provided_sa = request.data.get('submission_agreement')
                parsed_sa = parsed.get('altrecordids', {}).get('SUBMISSIONAGREEMENT', [None])[0]

                if parsed_sa is not None and provided_sa is not None:
                    if provided_sa == parsed_sa:
                        sa = provided_sa
                    else:
                        raise exceptions.ParseError(detail='Must use SA specified in XML')
                elif any([parsed_sa, provided_sa]):
                    sa = parsed_sa or provided_sa
                else:
                    raise exceptions.ParseError(detail='Missing parameter submission_agreement')

                try:
                    sa = SubmissionAgreement.objects.select_for_update().get(pk=sa)
                except (ValueError, ValidationError, SubmissionAgreement.DoesNotExist) as e:
                    raise exceptions.ParseError(e)

                ip = InformationPackage.objects.create(
                    object_identifier_value=pk,
                    submission_agreement=sa,
                    object_path=container,
                    package_mets_path=xmlfile,
                )
                parse_submit_description_from_ip(ip)

                member = Member.objects.get(django_user=request.user)
                user_perms = perms.pop('owner', [])

                organization.assign_object(ip, custom_permissions=perms)
                organization.add_object(ip)

                for perm in user_perms:
                    perm_name = get_permission_name(perm, ip)
                    assign_perm(perm_name, member.django_user, ip)
            else:
                ip = existing_sip
                sa = ip.submission_agreement

            ProfileIP.objects.select_for_update().filter(ip=ip).delete()
            sa.lock_to_information_package(ip, request.user)

        aic_xml = True
        if sa.profile_aic_description is None:
            aic_xml = False
            # raise exceptions.ParseError('Submission agreement missing AIC Description profile')

        if sa.profile_aip is None:
            raise exceptions.ParseError('Submission agreement missing AIP profile')

        if sa.profile_aip_description is None:
            raise exceptions.ParseError('Submission agreement missing AIP Description profile')

        if sa.profile_dip is None:
            raise exceptions.ParseError('Submission agreement missing DIP profile')

        ip.sip_objid = pk
        ip.sip_path = pk
        ip.package_type = InformationPackage.AIP
        if aic_xml:
            ip.generation = 0
            ip.aic = InformationPackage.objects.create(
                package_type=InformationPackage.AIC,
                responsible=ip.responsible,
                label=ip.label,
                start_date=ip.start_date,
                end_date=ip.end_date,
            )
        ip.state = 'At reception'
        ip.object_path = normalize_path(container)
        ip.package_mets_path = normalize_path(xmlfile)
        ip.responsible = request.user
        ip.save()

        return (ip, ip_is_directory)

    @transaction.atomic
    @permission_required_or_403(['ip.receive'])
    @method_decorator(feature_enabled_or_404('receive'))
    @action(detail=True, methods=['post'], url_path='receive')
    def receive(self, request, pk=None):
        logger = logging.getLogger('essarch.ingest')

        try:
            ip = InformationPackage.objects.select_for_update().get(
                object_identifier_value=pk,
                package_type=InformationPackage.AIP,
                state='At reception',
            )
            ip_is_directory = False
        except InformationPackage.DoesNotExist:
            ip, ip_is_directory = self._prepare(request, pk)

        ip.state = 'Receiving'
        ip.save(update_fields=['state'])

        # refresh date fields to convert them to datetime instances instead of
        # strings to allow further datetime manipulation
        ip.refresh_from_db(fields=['entry_date', 'start_date', 'end_date'])

        cts = ip.get_content_type_file()
        has_cts = cts is not None and os.path.exists(cts)

        aip_object_path = os.path.join(ip.policy.ingest_path.value, ip.object_identifier_value)
        aip_object_structure = ip.get_profile_rel('aip').profile.structure

        if ip_is_directory:
            workflow_spec = [
                {
                    "name": "ESSArch_Core.workflow.tasks.ReceiveDir",
                    "label": "Receive IP to workspace",
                },
                {
                    "name": "ESSArch_Core.tasks.UpdateIPSizeAndCount",
                    "label": "Update IP size and file count",
                },
                {
                    "name": "ESSArch_Core.tasks.UpdateIPStatus",
                    "label": "Set status to received",
                    "args": ["Received"],
                },
            ]
        else:
            workflow_spec = [
                {
                    "step":
                    True,
                    "name":
                    "Validation",
                    "children": [
                        {
                            "name": "ESSArch_Core.tasks.ValidateXMLFile",
                            "label": "Validate package-mets",
                            "params": {
                                "xml_filename": "{{_PACKAGE_METS_PATH}}",
                            }
                        },
                        {
                            "name": "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation",
                            "label": "Redundancy check against package-mets",
                            "args": ["{{_OBJPATH}}", "{{_PACKAGE_METS_PATH}}",
                                     ['{{_INNER_IP_PATH}}/dias-mets.xml']],
                        },
                        {
                            "name": "ESSArch_Core.tasks.ValidateXMLFile",
                            "label": "Validate cts",
                            "if": has_cts,
                            "run_if": "{{_CTS_PATH | path_exists}}",
                            "params": {
                                "xml_filename": "{{_CTS_PATH}}",
                                "schema_filename": "{{_CTS_SCHEMA_PATH}}",
                            }
                        },
                    ]
                },
                {
                    "name": "ESSArch_Core.ip.tasks.CreatePhysicalModel",
                    "label": "Create Physical Model",
                    'params': {
                        'structure': aip_object_structure,
                        'root': aip_object_path
                    }
                },
                {
                    "name": "ESSArch_Core.workflow.tasks.ReceiveSIP",
                    "label": "Receive SIP",
                    "params": {
                        'purpose': request.data.get('purpose'),
                    }
                },
                {
                    "name": "ESSArch_Core.tasks.UpdateIPSizeAndCount",
                    "label": "Update IP size and file count",
                },
                {
                    "name": "ESSArch_Core.tasks.UpdateIPStatus",
                    "label": "Set status to received",
                    "args": ["Received"],
                },
            ]

        workflow = create_workflow(workflow_spec, ip, name="Receive from reception")
        workflow.run()
        logger.info(
            'Started receiving {objid} from reception'.format(objid=ip.object_identifier_value),
            extra={'user': request.user.pk},
        )
        return Response({'detail': gettext('Receiving {ip}').format(ip=ip)})

    @transaction.atomic
    @method_decorator(feature_enabled_or_404('transfer'))
    @action(detail=True, methods=['post'], url_path='transfer', permission_classes=[CanTransferSIP])
    def transfer(self, request, pk=None):
        logger = logging.getLogger('essarch.ingest')
        perms = copy.deepcopy(getattr(settings, 'IP_CREATION_PERMS_MAP', {}))
        organization = request.user.user_profile.current_organization

        existing_ip = InformationPackage.objects.filter(object_identifier_value=pk).first()

        if existing_ip is not None:
            ip = existing_ip

            workflow_spec = [
                {
                    "name": "ESSArch_Core.tasks.UpdateIPStatus",
                    "label": "Set status to transferring",
                    "args": ["Transferring"],
                },
                {
                    "name": "ESSArch_Core.ip.tasks.TransferIP",
                    "label": "Transfer IP",
                },
                {
                    "name": "ESSArch_Core.tasks.UpdateIPStatus",
                    "label": "Set status to transferred",
                    "args": ["Transferred"],
                },
            ]
        else:
            reception = Path.objects.values_list('value', flat=True).get(entity='ingest_reception')
            xmlfile = normalize_path(os.path.join(reception, '%s.xml' % pk))

            if not os.path.isfile(xmlfile):
                logger.warning(
                    'Tried to transfer IP with missing XML file %s' % xmlfile,
                    extra={'user': request.user.pk}
                )
                raise exceptions.NotFound('%s does not exist' % xmlfile)
            try:
                container = normalize_path(os.path.join(reception, self.get_container_for_xml(xmlfile)))
            except etree.LxmlError:
                logger.warning(
                    'Tried to transfer IP with invalid XML file %s' % xmlfile,
                    extra={'user': request.user.pk}
                )
                raise exceptions.ParseError('Invalid XML file, %s' % xmlfile)

            if not os.path.isfile(container):
                logger.warning(
                    'Tried to transfer IP with missing container file %s' % container,
                    extra={'user': request.user.pk}
                )
                raise exceptions.NotFound('%s does not exist' % container)

            if organization is None:
                raise exceptions.ParseError('You must be part of an organization to transfer IP')

            parsed = parse_submit_description(xmlfile, srcdir=os.path.dirname(container))
            provided_sa = request.data.get('submission_agreement')
            parsed_sa = parsed.get('altrecordids', {}).get('SUBMISSIONAGREEMENT', [None])[0]

            if parsed_sa is not None and provided_sa is not None:
                if provided_sa == parsed_sa:
                    sa = provided_sa
                else:
                    raise exceptions.ParseError(detail='Must use SA specified in XML')
            elif any([parsed_sa, provided_sa]):
                sa = parsed_sa or provided_sa
            else:
                raise exceptions.ParseError(detail='Missing parameter submission_agreement')

            try:
                sa = SubmissionAgreement.objects.get(pk=sa)
            except (ValueError, ValidationError, SubmissionAgreement.DoesNotExist) as e:
                raise exceptions.ParseError(e)

            ip = InformationPackage.objects.create(
                object_identifier_value=pk,
                submission_agreement=sa,
                responsible=request.user,
                object_path=container,
                package_mets_path=normalize_path(xmlfile),
            )
            parse_submit_description_from_ip(ip)

            member = Member.objects.get(django_user=request.user)
            user_perms = perms.pop('owner', [])

            organization.assign_object(ip, custom_permissions=perms)
            organization.add_object(ip)

            for perm in user_perms:
                perm_name = get_permission_name(perm, ip)
                assign_perm(perm_name, member.django_user, ip)

            workflow_spec = [
                {
                    "name": "ESSArch_Core.tasks.UpdateIPStatus",
                    "label": "Set status to transferring",
                    "args": ["Transferring"],
                },
                {
                    "step": True,
                    "name": "Create Log File",
                    "children": [
                        {
                            "name": "ESSArch_Core.ip.tasks.GenerateEventsXML",
                            "label": "Generate events xml file",
                        },
                        {
                            "name": "ESSArch_Core.tasks.AppendEvents",
                            "label": "Add events to xml file",
                        },
                        {
                            "name": "ESSArch_Core.ip.tasks.AddPremisIPObjectElementToEventsFile",
                            "label": "Add premis IP object to xml file",
                        },

                    ]
                },
                {
                    "name": "ESSArch_Core.ip.tasks.TransferIP",
                    "label": "Transfer IP",
                },
                {
                    "name": "ESSArch_Core.tasks.UpdateIPStatus",
                    "label": "Set status to transferred",
                    "args": ["Transferred"],
                },
            ]
        workflow = create_workflow(workflow_spec, ip, name="Transfer IP")
        workflow.run()
        return Response({'status': 'transferring ip'})

    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        reception = Path.objects.get(entity='ingest_reception').value
        path = request.query_params.get('path', '').rstrip('/ ')
        download = request.query_params.get('download', False)
        if download is not False:
            download = string_to_bool(download)
        expand_container = request.query_params.get('expand_container', False)
        if expand_container is not False:
            expand_container = string_to_bool(expand_container)

        if os.path.isdir(os.path.join(reception, pk)):
            path = os.path.join(reception, pk, path)
            return list_files(path, force_download=download, expand_container=expand_container,
                              paginator=self.paginator, request=request)

        xml = os.path.join(reception, "%s.xml" % pk)

        if not os.path.exists(xml):
            raise exceptions.NotFound

        ip = parse_submit_description(xml, srcdir=reception)
        container = ip['object_path']

        if len(path):
            path = os.path.join(os.path.dirname(container), path)
            return list_files(path, force_download=download, expand_container=expand_container,
                              paginator=self.paginator, request=request)

        entry = {
            "name": os.path.basename(container),
            "type": 'file',
            "size": os.path.getsize(container),
            "modified": timestamp_to_datetime(os.path.getmtime(container)),
        }

        xmlentry = {
            "name": os.path.basename(xml),
            "type": 'file',
            "size": os.path.getsize(xml),
            "modified": timestamp_to_datetime(os.path.getmtime(xml)),
        }
        return Response([entry, xmlentry])

    @action(detail=False, methods=['post'])
    def upload(self, request):
        if not request.user.has_perm('ip.can_receive_remote_files'):
            raise exceptions.PermissionDenied

        path = Path.objects.get(entity='ingest_reception').value

        f = request.FILES['file']
        content_range = request.META.get('HTTP_CONTENT_RANGE', 'bytes 0-0/0')
        filename = os.path.join(path, f.name)

        (start, end, total) = parse_content_range_header(content_range)

        if f.size != end - start + 1:
            raise exceptions.ParseError("File size doesn't match headers")

        if start == 0:
            with open(filename, 'wb') as dstf:
                dstf.write(f.read())
        else:
            with open(filename, 'ab') as dstf:
                dstf.seek(start)
                dstf.write(f.read())

        upload_id = request.data.get('upload_id', uuid.uuid4().hex)
        return Response({'upload_id': upload_id})

    @action(detail=False, methods=['post'])
    def upload_complete(self, request):
        if not request.user.has_perm('ip.can_receive_remote_files'):
            raise exceptions.PermissionDenied

        path = Path.objects.get(entity='ingest_reception').value

        md5 = request.data['md5']
        filepath = request.data['path']
        filepath = os.path.join(path, filepath)

        options = {'expected': md5, 'algorithm': 'md5'}
        validator = ChecksumValidator(context='checksum_str', options=options)
        validator.validate(filepath)
        return Response({'detail': gettext('Upload of {filepath} complete').format(filepath=filepath)})

    def parse_ip_with_xmlfile(self, xmlfile):
        if xmlfile.startswith(self.uip):
            srcdir = self.uip
        else:
            srcdir = self.reception

        try:
            ip = parse_submit_description(xmlfile, srcdir)
        except (etree.LxmlError, ValueError):
            self.logger.exception('Failed to parse {}'.format(xmlfile))
            raise

        ip['state'] = 'At reception'
        ip['status'] = 100
        ip['step_state'] = celery_states.SUCCESS
        return ip

    def parse_unidentified_ip(self, container_file):
        ip = {
            'object_identifier_value': os.path.basename(container_file),
            'label': os.path.basename(container_file),
            'create_date': str(timestamp_to_datetime(creation_date(container_file)).isoformat()),
            'state': 'Unidentified',
            'status': 0,
            'step_state': celery_states.SUCCESS,
        }

        for xmlfile in glob.glob(os.path.join(self.uip, "*.xml")):
            if os.path.isfile(xmlfile):
                doc = etree.parse(xmlfile)
                root = doc.getroot()

                el = root.xpath('.//*[local-name()="%s"]' % "FLocat")[0]
                if ip['label'] == get_value_from_path(el, "@href").split('file:///')[1]:
                    raise exceptions.NotFound()

        return ip

    def parse_directory_ip(self, directory):
        ip = {
            'id': directory.name,
            'object_identifier_value': directory.name,
            'label': directory.name,
            'state': 'At reception',
            'status': 100,
            'step_state': celery_states.SUCCESS,
            'object_path': directory.path,
        }
        return ip

    def get_xml_files(self):
        return glob.glob(os.path.join(self.reception, "*.xml")) + glob.glob(os.path.join(self.uip, "*.xml"))

    def get_container_files(self):
        return glob.glob(os.path.join(self.uip, "*.tar")) + glob.glob(os.path.join(self.uip, "*.zip"))

    def get_directories(self):
        return get_immediate_subdirectories(self.reception)

    @action(detail=False, methods=['post'], url_path='identify-ip')
    def identify_ip(self, request):
        fname = request.data.get('filename')
        spec_data = request.data.get('specification_data', {})

        uip = Path.objects.get(entity="ingest_unidentified").value
        container_file = os.path.join(uip, fname)

        if not os.path.isfile(container_file):
            return Response(
                {'status': '%s does not exist' % container_file},
                status=status.HTTP_400_BAD_REQUEST
            )

        spec = json.loads(open(
            os.path.join(settings.BASE_DIR, 'templates/SDTemplate.json')
        ).read())

        objid = os.path.splitext(fname)[0]

        spec_data['_OBJID'] = spec_data.pop('ObjectIdentifierValue', objid)
        spec_data['_OBJLABEL'] = spec_data.pop('LABEL', objid)
        spec_data['_IP_CREATEDATE'] = timestamp_to_datetime(
            creation_date(container_file)
        ).isoformat()

        infoxml = '%s.xml' % objid
        infoxml = os.path.join(uip, infoxml)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': {
                    infoxml: {'spec': spec, 'data': spec_data}
                },
                'folderToParse': container_file,
            },
            responsible=request.user,
        ).run().get()

        return Response({'status': 'Identified IP, created %s' % infoxml})


class WorkareaViewSet(InformationPackageViewSet):
    queryset = InformationPackage.objects.select_related('responsible').all()

    def create(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)

    def annotate_filtered_first_generation(self, qs, workareas, user, see_all):
        lower_higher = InformationPackage.objects.visible_to_user(user).annotate(
            workarea_exists=Exists(workareas.filter(ip=OuterRef('pk')))
        ).filter(workarea_exists=True, aic=OuterRef('aic')).exclude(
            package_type=InformationPackage.AIC
        ).order_by().values('aic')

        if not see_all:
            lower_higher = lower_higher.filter(workareas__user=user)

        lower_higher = self.apply_filters(lower_higher).order_by()
        lower_higher = lower_higher.annotate(min_gen=Min('generation'))
        return qs.annotate(filtered_first_generation=self.first_generation_case(lower_higher))

    def get_related(self, qs, workareas):
        qs = qs.select_related('responsible')
        return qs.prefetch_related(
            'agents', 'steps',
            Prefetch('workareas', queryset=workareas, to_attr='prefetched_workareas')
        )

    def get_queryset(self):
        view_type = self.request.query_params.get('view_type', 'aic')
        user = self.request.user
        see_all = self.request.user.has_perm('ip.see_all_in_workspaces')

        workarea_params = {}
        for key, val in self.request.query_params.items():
            if key.startswith('workspace_'):
                key_suffix = remove_prefix(key, 'workspace_')
                workarea_params[key_suffix] = val

        workareas = Workarea.objects.all()
        workareas = WorkareaEntryFilter(data=workarea_params, queryset=workareas, request=self.request).qs
        if not see_all:
            workareas = workareas.filter(user=self.request.user)

        if self.action == 'list' and view_type == 'aic':
            simple_inner = InformationPackage.objects.visible_to_user(user).annotate(
                workarea_exists=Exists(workareas.filter(ip=OuterRef('pk')))
            ).filter(workarea_exists=True, active=True)

            simple_inner = self.apply_filters(simple_inner)

            inner = simple_inner.select_related('responsible').prefetch_related(
                'agents', 'steps',
                Prefetch('workareas', queryset=workareas, to_attr='prefetched_workareas')
            )
            dips = inner.filter(package_type=InformationPackage.DIP)

            lower_higher = InformationPackage.objects.filter(
                Q(aic=OuterRef('aic')), Q(Q(workareas=None) | Q(workareas__read_only=True))
            ).order_by().values('aic')
            lower_higher = lower_higher.annotate(min_gen=Min('generation'), max_gen=Max('generation'))

            inner = inner.annotate(first_generation=self.first_generation_case(lower_higher),
                                   last_generation=self.last_generation_case(lower_higher))

            simple_outer = InformationPackage.objects.annotate(
                has_ip=Exists(simple_inner.only('id').filter(aic=OuterRef('pk')))
            ).filter(package_type=InformationPackage.AIC, has_ip=True)
            aics = simple_outer.prefetch_related(Prefetch('information_packages', queryset=inner))

            if aics:
                self.queryset = aics
            else:
                self.queryset = dips
            # self.outer_queryset = simple_outer | dips
            # self.inner_queryset = simple_inner
            return self.queryset
        elif self.action == 'list' and view_type == 'ip':
            filtered = InformationPackage.objects.visible_to_user(user).annotate(
                workarea_exists=Exists(workareas.filter(ip=OuterRef('pk')))
            ).filter(workarea_exists=True, active=True).exclude(
                package_type=InformationPackage.AIC
            )

            simple = self.apply_filters(filtered)

            simple = self.annotate_generations(simple)
            simple = self.annotate_filtered_first_generation(simple, workareas, user, see_all)
            simple = self.get_related(simple, workareas)

            inner = simple.filter(filtered_first_generation=False)
            outer = simple.filter(filtered_first_generation=True).prefetch_related(
                Prefetch('aic__information_packages', queryset=inner)
            )

            # self.inner_queryset = simple
            # self.outer_queryset = simple
            self.queryset = outer
            return self.queryset
        elif self.action == 'list' and view_type == 'flat':
            qs = InformationPackage.objects.visible_to_user(user).annotate(
                workarea_exists=Exists(workareas.filter(ip=OuterRef('pk')))
            ).filter(workarea_exists=True, active=True).exclude(
                package_type=InformationPackage.AIC
            )
            qs = self.annotate_generations(self.apply_filters(qs))
            self.queryset = qs
            return self.queryset

        if self.action == 'retrieve':
            lower_higher = InformationPackage.objects.filter(
                Q(aic=OuterRef('aic'))
            ).order_by().values('aic')
            lower_higher = lower_higher.annotate(min_gen=Min('generation'), max_gen=Max('generation'))

            qs = InformationPackage.objects.visible_to_user(user).filter(
                active=True,
            )

            qs = self.apply_filters(qs)
            qs = qs.annotate(first_generation=self.first_generation_case(lower_higher),
                             last_generation=self.last_generation_case(lower_higher))
            qs = qs.select_related('responsible').prefetch_related(
                'agents', 'steps',
                Prefetch('workareas', to_attr='prefetched_workareas')
            )

            self.queryset = qs

        return self.queryset


class WorkareaFilesViewSet(viewsets.ViewSet, PaginatedViewMixin):
    permission_classes = (permissions.IsAuthenticated,)

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger('essarch.workspace')
        super().__init__(*args, **kwargs)

    def get_object(self, request):
        requested_id = self.request.query_params.get('id', self.request.data.get('id'))
        user_id = self.request.query_params.get('user', self.request.data.get('user'))
        try:
            obj = Workarea.objects.get(ip__id=requested_id, user__id=user_id)
        except Workarea.DoesNotExist:
            raise exceptions.NotFound
        return obj

    def get_user(self, request):
        requested_user = self.request.query_params.get('user', self.request.data.get('user'))
        if requested_user in EMPTY_VALUES or requested_user == str(request.user.pk):
            return request.user

        if not self.request.user.has_perm('ip.see_all_in_workspaces'):
            raise exceptions.PermissionDenied('No permission to see files in other users workspaces')

        try:
            user_id = requested_user
            organization = self.request.user.user_profile.current_organization
            organization_users = organization.get_members(subgroups=True)
            user = User.objects.get(pk=user_id, essauth_member__in=organization_users)
            return user
        except User.DoesNotExist:
            if requested_user is not None:
                user = User.objects.get(pk=requested_user)
            else:
                user = request.user
            raise exceptions.NotFound('User: {} not found in organization: {}'.format(
                user.username, organization.name))

    def validate_workarea(self, area_type):
        workarea_type_reverse = dict((v.lower(), k) for k, v in Workarea.TYPE_CHOICES)

        try:
            workarea_type_reverse[area_type]
        except KeyError:
            raise exceptions.ParseError('Workarea of type "%s" does not exist' % area_type)

    def validate_path(self, path, root, existence=True):
        path = os.path.normpath(path)
        root = os.path.normpath(root)
        relpath = os.path.relpath(path, root)

        if not in_directory(path, root):
            raise exceptions.ParseError('Illegal path %s' % relpath)

        if not path.startswith(root):
            raise exceptions.ParseError('Illegal path %s' % relpath)

        if existence and not os.path.exists(path):
            raise exceptions.NotFound('Path "%s" does not exist' % relpath)

    def list(self, request):
        try:
            workarea = request.query_params['type'].lower()
        except KeyError:
            raise exceptions.ParseError('Missing type parameter')

        self.validate_workarea(workarea)
        user = self.get_user(request)
        if request.query_params.get('id') in EMPTY_VALUES:
            root = os.path.join(Path.objects.get(entity=workarea + '_workarea').value, user.username)
        else:
            workarea_obj = self.get_object(request)
            root = workarea_obj.path
        os.makedirs(root, exist_ok=True)

        path = request.query_params.get('path', '').strip('/ ')
        force_download = request.query_params.get('download', False)
        if force_download is not False:
            force_download = string_to_bool(force_download)
        expand_container = request.query_params.get('expand_container', False)
        if expand_container is not False:
            expand_container = string_to_bool(expand_container)
        fullpath = os.path.join(root, path)

        try:
            self.validate_path(fullpath, root)
        except exceptions.NotFound:
            if len(fullpath.split('.tar/')) == 2:
                tar_path, tar_subpath = fullpath.split('.tar/')
                tar_path += '.tar'
                if not os.path.isfile(tar_path):
                    raise
            elif len(fullpath.split('.zip/')) == 2:
                zip_path, zip_subpath = fullpath.split('.zip/')
                zip_path += '.zip'
                if not os.path.isfile(zip_path):
                    raise
            else:
                raise

        return list_files(fullpath, force_download=force_download, expand_container=expand_container,
                          paginator=self.paginator, request=request)

    @action(detail=False, methods=['post'], url_path='add-directory')
    def add_directory(self, request):
        try:
            workarea = self.request.data['type'].lower()
        except KeyError:
            raise exceptions.ParseError('Missing type parameter')

        self.validate_workarea(workarea)
        workarea_obj = self.get_object(request)
        root = workarea_obj.path

        path = os.path.join(root, request.data.get('path', ''))
        self.validate_path(path, root, existence=False)

        if workarea_obj.read_only:
            detail = 'You are not allowed to modify read-only IPs'
            raise exceptions.MethodNotAllowed(method=request.method, detail=detail)

        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno == errno.EEXIST:
                raise exceptions.ParseError('Directory already exists')

        return Response(status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['delete'], url_path='')
    def delete(self, request):
        try:
            workarea = self.request.data['type'].lower()
        except KeyError:
            raise exceptions.ParseError('Missing type parameter')

        self.validate_workarea(workarea)
        workarea_obj = self.get_object(request)

        if workarea_obj.read_only:
            detail = 'You are not allowed to modify read-only IPs'
            raise exceptions.MethodNotAllowed(method=request.method, detail=detail)

        root = workarea_obj.path
        path = request.data.get('path', '')
        fullpath = os.path.normpath(os.path.join(root, path))
        self.validate_path(fullpath, root)
        try:
            shutil.rmtree(fullpath)
        except OSError as e:
            if e.errno != errno.ENOTDIR:
                raise
            os.remove(fullpath)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get', 'post'], url_path='upload')
    def upload(self, request):
        try:
            workarea = self.request.query_params['type'].lower()
        except KeyError:
            raise exceptions.ParseError('Missing type parameter')

        self.validate_workarea(workarea)
        workarea_obj = self.get_object(request)
        root = workarea_obj.path

        data = request.GET if request.method == 'GET' else request.data
        dst = data.get('destination', '').strip('/ ')

        self.validate_path(os.path.join(root, dst), root)

        if workarea_obj.read_only:
            detail = 'You are not allowed to modify read-only IPs'
            raise exceptions.MethodNotAllowed(method=request.method, detail=detail)

        relative_path = data.get('flowRelativePath', '')
        if len(relative_path) == 0:
            raise exceptions.ParseError('The path cannot be empty')

        try:
            chunk_nr = data['flowChunkNumber']
        except KeyError:
            raise exceptions.ParseError('flowChunkNumber parameter missing')

        path = os.path.join(dst, relative_path)
        chunk_path = "%s_%s" % (path, chunk_nr)

        temp_path = os.path.join(Path.objects.get(entity='temp').value, 'file_upload')
        full_chunk_path = os.path.join(temp_path, str(workarea_obj.pk), chunk_path)

        if request.method == 'GET':
            if os.path.exists(full_chunk_path):
                chunk_size = int(data.get('flowChunkSize'))
                if os.path.getsize(full_chunk_path) != chunk_size:
                    return Response(status=status.HTTP_400_BAD_REQUEST)
                return Response(status=status.HTTP_200_OK)

            return Response(status=status.HTTP_204_NO_CONTENT)

        if request.method == 'POST':
            chunk = request.FILES['file']
            os.makedirs(os.path.dirname(full_chunk_path), exist_ok=True)

            with open(full_chunk_path, 'wb+') as chunkf:
                for c in chunk.chunks():
                    chunkf.write(c)

            return Response("Uploaded chunk", status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='merge-uploaded-chunks')
    def merge_uploaded_chunks(self, request):
        try:
            workarea = self.request.query_params['type'].lower()
        except KeyError:
            raise exceptions.ParseError('Missing type parameter')

        self.validate_workarea(workarea)
        workarea_obj = self.get_object(request)
        root = workarea_obj.path
        relative_path = request.data.get('path', '')

        if len(relative_path) == 0:
            raise exceptions.ParseError('The path cannot be empty')

        filepath = os.path.join(root, relative_path)

        self.validate_path(filepath, root, existence=False)

        if workarea_obj.read_only:
            raise exceptions.MethodNotAllowed(request.method)

        temp_path = os.path.join(Path.objects.get(entity='temp').value, 'file_upload')
        chunks_path = os.path.join(temp_path, str(workarea_obj.pk), relative_path)

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        try:
            merge_file_chunks(chunks_path, filepath)
        except NoFileChunksFound:
            raise exceptions.NotFound('No chunks found')

        self.logger.info("Uploaded %s" % filepath)

        return Response({'detail': gettext('Merged chunks')})

    @action(detail=False, methods=['post'], url_path='add-to-dip')
    def add_to_dip(self, request):
        try:
            workarea = self.request.data['type'].lower()
        except KeyError:
            raise exceptions.ParseError('Missing type parameter')

        self.validate_workarea(workarea)
        try:
            user = self.get_user(request)
        except exceptions.NotFound as e:
            self.logger.warning('{}'.format(e))
            user = request.user

        root = os.path.join(Path.objects.get(entity=workarea + '_workarea').value, user.username)

        try:
            dip = self.request.data['dip']
        except KeyError:
            raise exceptions.ParseError('Missing dip parameter')

        try:
            ip = InformationPackage.objects.get(pk=dip, package_type=InformationPackage.DIP)

            permission = IsResponsibleOrReadOnly()
            if not permission.has_object_permission(request, self, ip):
                self.permission_denied(
                    request, message=getattr(permission, 'message', None)
                )
        except InformationPackage.DoesNotExist:
            raise exceptions.ParseError('DIP "%s" does not exist' % dip)

        try:
            src = self.request.data['src']
        except KeyError:
            raise exceptions.ParseError('Missing src parameter')

        try:
            dst = self.request.data['dst']
        except KeyError:
            raise exceptions.ParseError('Missing dst parameter')

        src = os.path.join(root, src)
        dst = os.path.join(ip.object_path, dst)

        try:
            self.validate_path(src, root)
        except exceptions.NotFound:
            if len(src.split('.tar/')) == 2:
                tar_path, tar_subpath = src.split('.tar/')
                tar_path += '.tar'
                if not os.path.isfile(tar_path):
                    raise
                with tarfile.open(tar_path) as tar:
                    try:
                        tarinfo_obj = tar.getmember(tar_subpath)
                        tarinfo_obj.name = tar_subpath.split('/')[-1]
                        tar.extract(tarinfo_obj, dst)
                        return Response(root)
                    except KeyError:
                        raise NotFound

            elif len(src.split('.zip/')) == 2:
                zip_path, zip_subpath = src.split('.zip/')
                zip_path += '.zip'
                if not os.path.isfile(zip_path):
                    raise
                with zipfile.ZipFile(zip_path) as zipf:
                    try:
                        zipinfo_obj = zipf.getinfo(zip_subpath)
                        zipinfo_obj.filename = zip_subpath.split('/')[-1]
                        zipf.extract(zipinfo_obj, dst)
                        return Response(root)
                    except KeyError:
                        raise NotFound
            else:
                raise

        if os.path.isfile(src):
            shutil.copy2(src, dst)
        else:
            try:
                shutil.copytree(src, dst)
            except OSError as e:
                if e.errno == errno.EEXIST:
                    shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    raise

        return Response(root)
