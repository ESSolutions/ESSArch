import os

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.auth.decorators import permission_required_or_403
from ESSArch_Core.auth.permissions import ActionPermissions
from ESSArch_Core.auth.util import get_objects_for_user
from ESSArch_Core.maintenance.filters import (AppraisalJobFilter,
                                              AppraisalRuleFilter,
                                              ConversionJobFilter,
                                              ConversionRuleFilter,
                                              MaintenanceJobFilter,
                                              MaintenanceRuleFilter)
from ESSArch_Core.maintenance.models import (AppraisalJob, AppraisalRule,
                                             ConversionJob, ConversionRule)
from ESSArch_Core.maintenance.serializers import (AppraisalJobSerializer,
                                                  AppraisalRuleSerializer,
                                                  ConversionJobSerializer,
                                                  ConversionRuleSerializer,
                                                  MaintenanceJobSerializer,
                                                  MaintenanceRuleSerializer)
from ESSArch_Core.util import generate_file_response


class MaintenanceRuleViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    permission_classes = (DjangoModelPermissions,)
    serializer_class = MaintenanceRuleSerializer
    filterset_class = MaintenanceRuleFilter
    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend, filters.SearchFilter,
    )
    search_fields = ('name', 'specification',)

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        public = qs.filter(public=True)
        local = get_objects_for_user(user, qs.filter(public=False), [])
        return public | local


class MaintenanceJobViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    permission_classes = (ActionPermissions,)
    serializer_class = MaintenanceJobSerializer
    filterset_class = MaintenanceJobFilter
    filter_backends = (filters.OrderingFilter, DjangoFilterBackend)

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        job = self.get_object()
        job.start_date = timezone.now()
        job.save()
        job.run()
        return Response(status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        path = self.get_report_pdf_path(pk)
        return generate_file_response(open(path, 'rb'), 'application/pdf')

    def get_report_pdf_path(self, pk):
        path = self.get_object()._get_report_directory()
        path = os.path.join(path, pk + '.pdf')
        return path


class AppraisalRuleViewSet(MaintenanceRuleViewSet):
    queryset = AppraisalRule.objects.all()
    serializer_class = AppraisalRuleSerializer
    filterset_class = AppraisalRuleFilter


class AppraisalJobViewSet(MaintenanceJobViewSet):
    queryset = AppraisalJob.objects.all()
    serializer_class = AppraisalJobSerializer
    filterset_class = AppraisalJobFilter

    @permission_required_or_403(['maintenance.run_appraisaljob'])
    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        return super().run(request, pk)

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        job = self.get_object()
        found_files = job.rule.get_job_preview_files()
        return Response(found_files)


class ConversionRuleViewSet(MaintenanceRuleViewSet):
    queryset = ConversionRule.objects.all()
    serializer_class = ConversionRuleSerializer
    filterset_class = ConversionRuleFilter


class ConversionJobViewSet(MaintenanceJobViewSet):
    queryset = ConversionJob.objects.all()
    serializer_class = ConversionJobSerializer
    filterset_class = ConversionJobFilter

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        job = self.get_object()
        found_files = job.rule.get_job_preview_files()
        return Response(found_files)
