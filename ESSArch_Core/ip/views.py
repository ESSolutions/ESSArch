import copy
import errno
import itertools
import logging
import os
import shutil

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from groups_manager.utils import get_permission_name
from guardian.shortcuts import assign_perm
from rest_framework import exceptions, filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask
from ESSArch_Core.WorkflowEngine.serializers import ProcessStepChildrenSerializer
from ESSArch_Core.WorkflowEngine.util import create_workflow
from ESSArch_Core.api.filters import string_to_bool
from ESSArch_Core.auth.decorators import permission_required_or_403
from ESSArch_Core.auth.serializers import ChangeOrganizationSerializer
from ESSArch_Core.auth.models import Member
from ESSArch_Core.configuration.models import Path
from ESSArch_Core.exceptions import Conflict, NoFileChunksFound
from ESSArch_Core.fixity.transformation import AVAILABLE_TRANSFORMERS
from ESSArch_Core.fixity.validation import AVAILABLE_VALIDATORS
from ESSArch_Core.ip.filters import AgentFilter, EventIPFilter, InformationPackageFilter
from ESSArch_Core.ip.models import Agent, EventIP, InformationPackage, Order, Workarea
from ESSArch_Core.ip.permissions import (
    CanChangeSA,
    CanCreateSIP,
    CanDeleteIP,
    CanSetUploaded,
    CanSubmitSIP,
    CanUnlockProfile,
    CanUpload,
    IsOrderResponsibleOrAdmin,
    IsResponsibleOrCanSeeAllFiles,
)
from ESSArch_Core.ip.serializers import (
    AgentSerializer,
    EventIPSerializer,
    InformationPackageSerializer,
    OrderSerializer,
    WorkareaSerializer
)
from ESSArch_Core.mixins import GetObjectForUpdateViewMixin
from ESSArch_Core.profiles.models import ProfileIP
from ESSArch_Core.util import find_destination, in_directory, merge_file_chunks, normalize_path


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    filter_backends = (filters.OrderingFilter, DjangoFilterBackend, filters.SearchFilter,)
    filterset_class = AgentFilter


class EventIPViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows events to be viewed or edited.
    """
    queryset = EventIP.objects.all()
    serializer_class = EventIPSerializer
    permission_classes = (DjangoModelPermissions,)
    filterset_class = EventIPFilter
    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend, filters.SearchFilter,
    )
    ordering_fields = (
        'id', 'eventType', 'eventOutcomeDetailNote', 'eventOutcome',
        'linkingAgentIdentifierValue', 'eventDateTime',
    )
    search_fields = ('eventOutcomeDetailNote',)


class WorkareaEntryViewSet(mixins.DestroyModelMixin, viewsets.ReadOnlyModelViewSet):

    queryset = Workarea.objects.all()
    serializer_class = WorkareaSerializer

    def get_queryset(self):
        see_all = self.request.user.has_perm('ip.see_all_in_workspaces')
        ips = InformationPackage.objects.visible_to_user(self.request.user)

        qs = self.queryset.filter(ip__in=ips)
        if not see_all:
            qs = qs.filter(user=self.request.user)

        return qs

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
            raise exceptions.ParseError(u"Transformer {} not in config".format(transformer))

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

        if not workarea.read_only:
            workarea.ip.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return super().destroy(request, pk, **kwargs)


class InformationPackageViewSet(viewsets.ModelViewSet, GetObjectForUpdateViewMixin):
    """
    API endpoint that allows information packages to be viewed or edited.
    """

    logger = logging.getLogger('essarch.InformationPackageViewSet')

    queryset = InformationPackage.objects.none()
    serializer_class = InformationPackageSerializer
    filter_backends = (filters.OrderingFilter, DjangoFilterBackend, filters.SearchFilter,)
    ordering_fields = (
        'label', 'responsible', 'create_date', 'state',
        'id', 'object_identifier_value', 'start_date', 'end_date',
    )
    search_fields = (
        'object_identifier_value', 'label', 'responsible__first_name',
        'responsible__last_name', 'responsible__username', 'state',
        'submission_agreement__name', 'start_date', 'end_date',
        'aic__object_identifier_value', 'aic__label',
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

    def get_queryset(self):
        user = self.request.user
        queryset = InformationPackage.objects.visible_to_user(user)
        queryset = queryset.prefetch_related(
            Prefetch('profileip_set', to_attr='profiles'), 'profiles__profile', 'agents',
            'responsible__user_permissions', 'responsible__groups__permissions', 'steps',
        ).select_related('submission_agreement')
        return queryset

    @action(detail=True, methods=['post'], url_path='change-organization')
    def change_organization(self, request, pk=None):
        ip = self.get_object()

        serializer = ChangeOrganizationSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        org = serializer.validated_data['organization']

        ip.change_organization(org)
        return Response()

    @action(detail=True)
    def workflow(self, request, pk=None):
        ip = self.get_object()
        hidden = request.query_params.get('hidden')

        steps = ip.steps.filter(parent_step__information_package__isnull=True)
        tasks = ip.processtask_set.filter(processstep__information_package__isnull=True)

        if hidden is not None:
            steps = steps.filter(hidden=string_to_bool(hidden))
            tasks = tasks.filter(hidden=string_to_bool(hidden))

        flow = sorted(itertools.chain(steps, tasks), key=lambda x: (x.get_pos(), x.time_created))

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

        try:
            label = request.data['label']
        except KeyError:
            raise exceptions.ParseError('Missing parameter label')

        object_identifier_value = request.data.get('object_identifier_value')
        responsible = self.request.user

        if responsible.user_profile.current_organization is None:
            raise exceptions.ParseError('You must be part of an organization to prepare an IP')

        prepare_path = Path.objects.get(entity="path_preingest_prepare").value
        if object_identifier_value:
            ip_exists = InformationPackage.objects.filter(object_identifier_value=object_identifier_value).exists()
            if ip_exists:
                raise Conflict('IP with object identifer value "%s" already exists' % object_identifier_value)

            if os.path.exists(os.path.join(prepare_path, object_identifier_value)):
                raise Conflict('IP with identifier "%s" already exists on disk' % object_identifier_value)

        perms = copy.deepcopy(getattr(settings, 'IP_CREATION_PERMS_MAP', {}))
        try:
            with transaction.atomic():
                ip = InformationPackage.objects.create(object_identifier_value=object_identifier_value, label=label,
                                                       responsible=responsible, state="Preparing",
                                                       package_type=InformationPackage.SIP)
                ip.entry_date = ip.create_date
                extra = {
                    'event_type': 10100,
                    'object': str(ip.pk),
                    'agent': request.user.username,
                    'outcome': EventIP.SUCCESS
                }
                self.logger.info("Prepared {obj}".format(obj=ip.object_identifier_value), extra=extra)

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
        ip = self.get_object_for_update()
        if ip.is_locked():
            raise Conflict('Information package is locked')
        sa = ip.submission_agreement

        if ip.state != 'Preparing':
            raise exceptions.ParseError('IP must be in state "Preparing"')

        if sa is None or not ip.submission_agreement_locked:
            raise exceptions.ParseError('IP requires locked SA to be prepared')

        profile_ip_sip = ProfileIP.objects.filter(ip=ip, profile=sa.profile_sip).first()
        profile_ip_transfer_project = ProfileIP.objects.filter(ip=ip, profile=sa.profile_transfer_project).first()
        profile_ip_submit_description = ProfileIP.objects.filter(ip=ip, profile=sa.profile_submit_description).first()

        if profile_ip_sip is None:
            raise exceptions.ParseError('Information package missing SIP profile')
        if profile_ip_transfer_project is None:
            raise exceptions.ParseError('Information package missing Transfer Project profile')
        if profile_ip_submit_description is None:
            raise exceptions.ParseError('Information package missing Submit Description profile')

        for profile_ip in ProfileIP.objects.filter(ip=ip).iterator():
            try:
                profile_ip.clean()
            except ValidationError as e:
                raise exceptions.ParseError('%s: %s' % (profile_ip.profile.name, e[0]))

            profile_ip.LockedBy = request.user
            profile_ip.save()

        step = ProcessStep.objects.create(
            name="Create Physical Model",
            information_package=ip
        )
        ProcessTask.objects.create(
            name="ESSArch_Core.ip.tasks.CreatePhysicalModel",
            information_package=ip,
            responsible=self.request.user,
            processstep=step,
        )

        step.run().get()

        submit_description_data = ip.get_profile_data('submit_description')
        ip.start_date = submit_description_data.get('start_date')
        ip.end_date = submit_description_data.get('end_date')

        ip.state = "Prepared"
        ip.save(update_fields=['state', 'start_date', 'end_date'])

        return Response()

    @action(detail=True, methods=['get', 'post'], url_path='upload', permission_classes=[CanUpload])
    def upload(self, request, pk=None):
        ip = self.get_object()
        if ip.state not in ['Prepared', 'Uploading']:
            raise exceptions.ParseError('IP must be in state "Prepared" or "Uploading"')

        ip.state = "Uploading"
        ip.save()

        if request.method == 'GET':
            dst = request.GET.get('destination', '').strip('/ ')
            path = os.path.join(dst, request.GET.get('flowRelativePath', ''))
            chunk_nr = request.GET.get('flowChunkNumber')
            chunk_path = "%s_%s" % (path, chunk_nr)

            if os.path.exists(os.path.join(ip.object_path, chunk_path)):
                return Response()
            return Response(status=status.HTTP_204_NO_CONTENT)

        if request.method == 'POST':
            dst = request.data.get('destination', '').strip('/ ')
            path = os.path.join(dst, request.data.get('flowRelativePath', ''))
            chunk_nr = request.data.get('flowChunkNumber')
            chunk_path = "%s_%s" % (path, chunk_nr)
            chunk_path = os.path.join(ip.object_path, chunk_path)

            chunk = request.FILES['file']

            if not os.path.exists(os.path.dirname(chunk_path)):
                os.makedirs(os.path.dirname(chunk_path), exist_ok=True)

            with open(chunk_path, 'wb+') as dst:
                for c in chunk.chunks():
                    dst.write(c)

            return Response("Uploaded chunk")

    @action(detail=True, methods=['post'], url_path='merge-uploaded-chunks', permission_classes=[CanUpload])
    def merge_uploaded_chunks(self, request, pk=None):
        ip = self.get_object()
        if ip.state != 'Uploading':
            raise exceptions.ParseError('IP must be in state "Uploading"')

        path = os.path.join(ip.object_path, request.data['path'])

        try:
            merge_file_chunks(path)
        except NoFileChunksFound:
            raise exceptions.NotFound('No chunks found')

        logger = logging.getLogger('essarch')
        extra = {'event_type': 50700, 'object': str(ip.pk), 'agent': request.user.username, 'outcome': EventIP.SUCCESS}
        logger.info("Uploaded %s" % path, extra=extra)

        return Response("Merged chunks")

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='set-uploaded', permission_classes=[CanSetUploaded])
    def set_uploaded(self, request, pk=None):
        ip = self.get_object()
        if ip.state not in ['Prepared', 'Uploading']:
            raise exceptions.ParseError('IP must be in state "Prepared" or "Uploading"')

        ProcessTask.objects.create(
            name="ESSArch_Core.tasks.UpdateIPSizeAndCount",
            eager=False,
            information_package=ip
        ).run()

        ip.state = "Uploaded"
        ip.save()
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

        ip = self.get_object_for_update()
        if ip.is_locked():
            raise Conflict('Information package is locked')

        if ip.state != "Uploaded":
            raise exceptions.ParseError("The IP (%s) is in the state '%s' but should be 'Uploaded'" % (pk, ip.state))

        ip.state = 'Creating'
        ip.save()

        generate_premis = ip.profile_locked('preservation_metadata')

        convert_files = request.data.get('file_conversion', False)
        file_format_map = {
            'doc': 'pdf',
            'docx': 'pdf'
        }

        validators = request.data.get('validators', {})
        validate_xml_file = validators.get('validate_xml_file', False)
        validate_logical_physical_representation = validators.get('validate_logical_physical_representation', False)

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
                "name": "ESSArch_Core.ip.tasks.GeneratePremis",
                "if": generate_premis,
                "label": "Generate premis",
            },
            {
                "name": "ESSArch_Core.ip.tasks.GenerateContentMets",
                "label": "Generate content-mets",
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
                        "label": "Diff-check against content-mets",
                        "args": ["{{_OBJPATH}}", "{{_CONTENT_METS_PATH}}"],
                    },
                    {
                        "name": "ESSArch_Core.tasks.CompareXMLFiles",
                        "if": generate_premis,
                        "label": "Compare premis and content-mets",
                        "args": ["{{_PREMIS_PATH}}", "{{_CONTENT_METS_PATH}}"],
                    }
                ]
            },
            {
                "name": "ESSArch_Core.ip.tasks.CreateContainer",
                "label": "Create container",
            },
            {
                "name": "ESSArch_Core.tasks.UpdateIPStatus",
                "label": "Set status to created",
                "args": ["Created"],
            },
        ]
        workflow = create_workflow(workflow_spec, ip)
        workflow.name = "Create SIP"
        workflow.information_package = ip
        workflow.save()
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

        ip = self.get_object_for_update()
        if ip.is_locked():
            raise Conflict('Information package is locked')

        if ip.state != "Created":
            return Response(
                "The IP (%s) is in the state '%s' but should be 'Created'" % (pk, ip.state),
                status=status.HTTP_400_BAD_REQUEST
            )

        ip.state = 'Submitting'
        ip.save()

        sd_profile = ip.get_profile('submit_description')

        if sd_profile is None:
            return Response(
                "The IP (%s) has no submit description profile" % pk,
                status=status.HTTP_400_BAD_REQUEST
            )

        email_subject = None
        email_body = None
        recipient = ip.get_email_recipient()
        if recipient:
            for arg in ['subject', 'body']:
                if arg not in request.data:
                    raise exceptions.ParseError('%s parameter missing' % arg)

            email_subject = request.data['subject']
            email_body = request.data['body']

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
                "label": "Diff-check against package-mets",
                "args": ["{{_OBJPATH}}", "{{_PACKAGE_METS_PATH}}"],
            },
            {
                "name": "ESSArch_Core.ip.tasks.SubmitSIP",
                "label": "Submit SIP",
            },
            {
                "name": "ESSArch_Core.tasks.UpdateIPStatus",
                "label": "Set status to submitted",
                "args": ["Submitted"],
            },
            {
                "name": "ESSArch_Core.tasks.SendEmail",
                "if": recipient,
                "label": "Send email",
                "params": {
                    "subject": email_subject,
                    "body": email_body,
                    "recipients": [recipient],
                    "attachments": [
                        "{{_PACKAGE_METS_PATH}}",
                    ],
                }
            },
        ]
        workflow = create_workflow(workflow_spec, ip)
        workflow.name = "Submit SIP"
        workflow.information_package = ip
        workflow.save()
        workflow.run()
        return Response({'status': 'submitting ip'})


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
