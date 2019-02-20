import itertools

from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import exceptions, filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask
from ESSArch_Core.WorkflowEngine.serializers import ProcessStepChildrenSerializer
from ESSArch_Core.auth.serializers import ChangeOrganizationSerializer
from ESSArch_Core.filters import string_to_bool
from ESSArch_Core.fixity.transformation import AVAILABLE_TRANSFORMERS
from ESSArch_Core.fixity.validation import AVAILABLE_VALIDATORS
from ESSArch_Core.ip.filters import AgentFilter, EventIPFilter, InformationPackageFilter
from ESSArch_Core.ip.models import Agent, EventIP, InformationPackage, Workarea
from ESSArch_Core.ip.permissions import CanChangeSA, CanDeleteIP
from ESSArch_Core.ip.serializers import (
    AgentSerializer,
    EventIPSerializer,
    InformationPackageSerializer,
    WorkareaSerializer
)
from ESSArch_Core.profiles.models import ProfileIP


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


class InformationPackageViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows information packages to be viewed or edited.
    """
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
