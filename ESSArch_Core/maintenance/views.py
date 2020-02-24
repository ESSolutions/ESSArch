from celery import states as celery_states
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.api.filters import SearchFilter
from ESSArch_Core.auth.decorators import permission_required_or_403
from ESSArch_Core.auth.permissions import ActionPermissions
from ESSArch_Core.auth.util import get_objects_for_user
from ESSArch_Core.exceptions import Locked
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.maintenance.filters import (
    AppraisalJobFilter,
    AppraisalTemplateFilter,
    ConversionJobFilter,
    ConversionTemplateFilter,
    MaintenanceJobFilter,
    MaintenanceTemplateFilter,
)
from ESSArch_Core.maintenance.models import (
    AppraisalJob,
    AppraisalTemplate,
    ConversionJob,
    ConversionTemplate,
)
from ESSArch_Core.maintenance.serializers import (
    AppraisalJobInformationPackageSerializer,
    AppraisalJobInformationPackageWriteSerializer,
    AppraisalJobSerializer,
    AppraisalJobTagSerializer,
    AppraisalJobTagWriteSerializer,
    AppraisalTemplateSerializer,
    ConversionJobSerializer,
    ConversionTemplateSerializer,
    MaintenanceJobSerializer,
    MaintenanceTemplateSerializer,
)
from ESSArch_Core.tags.models import Tag
from ESSArch_Core.util import generate_file_response
from ESSArch_Core.WorkflowEngine.models import ProcessTask


class MaintenanceTemplateViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    permission_classes = (ActionPermissions,)
    serializer_class = MaintenanceTemplateSerializer
    filterset_class = MaintenanceTemplateFilter
    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend, SearchFilter,
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

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        job = self.get_object()
        found_files = job.preview()
        return Response(found_files)

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        job = self.get_object()
        job.task.run()
        return Response(status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        path = self.get_object().get_report_pdf_path()
        return generate_file_response(open(path, 'rb'), 'application/pdf')

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.status == celery_states.STARTED:
            raise Locked
        return super().destroy(request, *args, **kwargs)


class AppraisalTemplateViewSet(MaintenanceTemplateViewSet):
    queryset = AppraisalTemplate.objects.all()
    serializer_class = AppraisalTemplateSerializer
    filterset_class = AppraisalTemplateFilter


class AppraisalJobViewSet(MaintenanceJobViewSet):
    queryset = AppraisalJob.objects.all()
    serializer_class = AppraisalJobSerializer
    filterset_class = AppraisalJobFilter

    @permission_required_or_403(['maintenance.run_appraisaljob'])
    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        job = self.get_object()
        if job.task is None:
            job.task = ProcessTask.objects.create(
                name='ESSArch_Core.maintenance.tasks.RunAppraisalJob',
                args=[str(job.pk)],
                eager=False,
            )
            job.save(update_fields=['task'])

        return super().run(request, pk)


class AppraisalJobInformationPackageViewSet(NestedViewSetMixin,
                                            mixins.CreateModelMixin,
                                            mixins.ListModelMixin,
                                            viewsets.GenericViewSet):

    queryset = InformationPackage.objects.all()
    serializer_class = AppraisalJobInformationPackageSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        job = AppraisalJob.objects.get(pk=self.get_parents_query_dict()['appraisal_jobs'])
        job.information_packages.set(data['information_packages'])

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        job = AppraisalJob.objects.get(pk=self.get_parents_query_dict()['appraisal_jobs'])
        job.information_packages.add(*data['information_packages'])

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    def delete(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        job = AppraisalJob.objects.get(pk=self.get_parents_query_dict()['appraisal_jobs'])
        job.information_packages.remove(*data['information_packages'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_serializer_class(self):
        if self.request.method in ['POST', 'PATCH', 'DELETE']:
            return AppraisalJobInformationPackageWriteSerializer

        return self.serializer_class


class AppraisalJobTagViewSet(NestedViewSetMixin,
                             mixins.CreateModelMixin,
                             mixins.ListModelMixin,
                             viewsets.GenericViewSet):

    queryset = Tag.objects.select_related('current_version').all()
    serializer_class = AppraisalJobTagSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (filters.OrderingFilter,)
    ordering = ('current_version__reference_code',)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        job = AppraisalJob.objects.get(pk=self.get_parents_query_dict()['appraisal_jobs'])
        job.tags.set(data['tags'])

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        job = AppraisalJob.objects.get(pk=self.get_parents_query_dict()['appraisal_jobs'])
        job.tags.add(*data['tags'])

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    def delete(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        job = AppraisalJob.objects.get(pk=self.get_parents_query_dict()['appraisal_jobs'])
        job.tags.remove(*data['tags'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_serializer_class(self):
        if self.request.method in ['POST', 'PATCH', 'DELETE']:
            return AppraisalJobTagWriteSerializer

        return self.serializer_class


class ConversionTemplateViewSet(MaintenanceTemplateViewSet):
    queryset = ConversionTemplate.objects.all()
    serializer_class = ConversionTemplateSerializer
    filterset_class = ConversionTemplateFilter


class ConversionJobViewSet(MaintenanceJobViewSet):
    queryset = ConversionJob.objects.all()
    serializer_class = ConversionJobSerializer
    filterset_class = ConversionJobFilter

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        job = self.get_object()
        if job.task is None:
            job.task = ProcessTask.objects.create(
                name='ESSArch_Core.maintenance.tasks.RunConversionJob',
                args=[str(job.pk)],
                eager=False,
            )
            job.save(update_fields=['task'])

        return super().run(request, pk)
