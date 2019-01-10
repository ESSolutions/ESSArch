import os

import six
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from glob2 import iglob
from rest_framework import filters, status, viewsets
from rest_framework.decorators import detail_route
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin
from os import walk

from ESSArch_Core.auth.decorators import permission_required_or_403
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
        qs = super(MaintenanceRuleViewSet, self).get_queryset()
        public = qs.filter(public=True)
        local = get_objects_for_user(user, qs.filter(public=False), [])
        return public | local


class MaintenanceJobViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    permission_classes = (DjangoModelPermissions,)
    serializer_class = MaintenanceJobSerializer
    filterset_class = MaintenanceJobFilter
    filter_backends = (filters.OrderingFilter, DjangoFilterBackend)

    @detail_route(methods=['post'])
    def run(self, request, pk=None):
        job = self.get_object()
        job.start_date = timezone.now()
        job.save()
        job.run()
        return Response(status=status.HTTP_202_ACCEPTED)

    @detail_route(methods=['get'])
    def report(self, request, pk=None):
        path = self.get_object()._get_report_directory()
        path = os.path.join(path, pk + '.pdf')
        return generate_file_response(open(path, 'rb'), 'application/pdf')


class AppraisalRuleViewSet(MaintenanceRuleViewSet):
    queryset = AppraisalRule.objects.all()
    serializer_class = AppraisalRuleSerializer
    filterset_class = AppraisalRuleFilter


class AppraisalJobViewSet(MaintenanceJobViewSet):
    queryset = AppraisalJob.objects.all()
    serializer_class = AppraisalJobSerializer
    filterset_class = AppraisalJobFilter

    @permission_required_or_403(['maintenance.run_appraisaljob'])
    @detail_route(methods=['post'])
    def run(self, request, pk=None):
        return super(AppraisalJobViewSet, self).run(request, pk)

    @detail_route(methods=['get'])
    def preview(self, request, pk=None):
        job = self.get_object()
        ips = job.rule.information_packages.filter(appraisal_date__lte=timezone.now(), active=True)
        found = []

        for ip in ips:
            datadir = os.path.join(ip.policy.cache_storage.value, ip.object_identifier_value)
            if job.rule.specification:
                for pattern in job.rule.specification:
                    for path in iglob(datadir + '/' + pattern):
                        if os.path.isdir(path):
                            for root, dirs, files in walk(path):
                                rel = os.path.relpath(root, datadir)

                                for f in files:
                                    found.append({'ip': ip.object_identifier_value, 'document': os.path.join(rel, f)})

                        elif os.path.isfile(path):
                            rel = os.path.relpath(path, datadir)
                            found.append({'ip': ip.object_identifier_value, 'document': rel})
            else:
                for root, dirs, files in walk(datadir):
                    rel = os.path.relpath(root, datadir)

                    for f in files:
                        found.append({'ip': ip.object_identifier_value, 'document': os.path.join(rel, f)})
        return Response(found)


class ConversionRuleViewSet(MaintenanceRuleViewSet):
    queryset = ConversionRule.objects.all()
    serializer_class = ConversionRuleSerializer
    filterset_class = ConversionRuleFilter


class ConversionJobViewSet(MaintenanceJobViewSet):
    queryset = ConversionJob.objects.all()
    serializer_class = ConversionJobSerializer
    filterset_class = ConversionJobFilter

    @detail_route(methods=['get'])
    def preview(self, request, pk=None):
        job = self.get_object()
        ips = job.rule.information_packages.all()
        files = []

        for ip in ips:
            datadir = os.path.join(ip.policy.cache_storage.value, ip.object_identifier_value)
            for pattern, spec in six.iteritems(job.rule.specification):
                for path in iglob(datadir + '/' + pattern):
                    if os.path.isdir(path):
                        for root, dirs, files in walk(path):
                            rel = os.path.relpath(root, datadir)

                            for f in files:
                                files.append({'ip': ip.object_identifier_value, 'document': os.path.join(rel, f)})

                    elif os.path.isfile(path):
                        rel = os.path.relpath(path, datadir)
                        files.append({'ip': ip.object_identifier_value, 'document': rel})

        return Response(files)
