"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import itertools

from celery import states as celery_states
from django.db import transaction
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import exceptions, viewsets
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.auth.permissions import ActionPermissions
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.WorkflowEngine.filters import (
    ProcessStepFilter,
    ProcessTaskFilter,
)
from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask
from ESSArch_Core.WorkflowEngine.permissions import (
    CanRetry,
    CanRevoke,
    CanRun,
    CanUndo,
)
from ESSArch_Core.WorkflowEngine.serializers import (
    ProcessStepChildrenSerializer,
    ProcessStepDetailSerializer,
    ProcessStepSerializer,
    ProcessTaskDetailSerializer,
    ProcessTaskSerializer,
)


class ProcessViewSet(GenericAPIView, viewsets.ViewSet):
    queryset = ProcessStep.objects.none()

    def list(self, request, parent_lookup_processstep):
        step = ProcessStep.objects.get(pk=parent_lookup_processstep)
        child_steps = step.child_steps.all()
        child_steps = ProcessStepFilter(data=request.query_params, queryset=child_steps, request=self.request).qs

        tasks = step.tasks.all().select_related('responsible')
        tasks = ProcessTaskFilter(data=request.query_params, queryset=tasks, request=self.request).qs

        queryset = sorted(
            itertools.chain(child_steps, tasks),
            key=lambda instance: instance.get_pos()
        )

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializers = ProcessStepChildrenSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializers.data)

        serializers = ProcessStepChildrenSerializer(queryset, many=True, context={'request': request})
        return Response(serializers.data)


class ProcessStepViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows steps to be viewed or edited.
    """
    queryset = ProcessStep.objects.none()
    serializer_class = ProcessStepSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ProcessStepFilter

    def get_queryset(self):
        user = self.request.user
        ips = InformationPackage.objects.visible_to_user(user)
        queryset = ProcessStep.objects.filter(
            Q(information_package__in=ips) | Q(information_package__isnull=True)).distinct()
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ProcessStepSerializer

        return ProcessStepDetailSerializer

    @action(detail=True, methods=['get'], url_path='child-steps')
    def child_steps(self, request, pk=None):
        step = self.get_object()
        child_steps = step.child_steps.all()
        page = self.paginate_queryset(child_steps)
        if page is not None:
            serializers = ProcessStepSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializers.data)
        serializers = ProcessStepSerializer(child_steps, many=True, context={'request': request})
        return Response(serializers.data)


class ProcessTaskViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows tasks to be viewed or edited.
    """
    queryset = ProcessTask.objects.none()
    serializer_class = ProcessTaskSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ProcessTaskFilter

    def get_queryset(self):
        user = self.request.user
        ips = InformationPackage.objects.visible_to_user(user)
        queryset = ProcessTask.objects.select_related('responsible').filter(
            Q(information_package__in=ips) | Q(information_package__isnull=True)
        ).distinct()
        return self.filter_queryset_by_parents_lookups(queryset)

    def get_serializer_class(self):
        if self.action in ['create', 'list']:
            return ProcessTaskSerializer

        return ProcessTaskDetailSerializer

    @transaction.atomic
    @action(detail=True, methods=['post'], permission_classes=[CanRun])
    def run(self, request, pk=None):
        self.get_object().run()
        return Response({'status': 'running task'})

    @action(detail=True, methods=['post'], permission_classes=[CanRevoke])
    def revoke(self, request, pk=None):
        obj = self.get_object()
        if obj.status != celery_states.STARTED:
            raise exceptions.ParseError('Only running tasks can be revoked')

        obj.revoke()
        return Response({'status': 'revoked task'})

    @action(detail=True, methods=['post'], permission_classes=[CanRetry])
    def retry(self, request, pk=None):
        obj = self.get_object()
        if obj.status not in celery_states.EXCEPTION_STATES:
            raise exceptions.ParseError('Only failed tasks can be retried')

        root = obj.get_root_step()
        if root is not None:
            root.resume()
        else:
            obj.retry()

        return Response({'status': 'retries task'})

    @transaction.atomic
    @action(detail=True, methods=['post'], permission_classes=[CanUndo])
    def undo(self, request, pk=None):
        self.get_object().undo()
        return Response({'status': 'undoing task'})
