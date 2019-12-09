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

import os
import uuid

from django.contrib.auth.models import User
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import exceptions, filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from ESSArch_Core.api.filters import SearchFilter
from ESSArch_Core.configuration.models import Path, StoragePolicy
from ESSArch_Core.configuration.serializers import (
    StorageMethodSerializer,
    StorageMethodTargetRelationSerializer,
    StorageTargetSerializer,
)
from ESSArch_Core.exceptions import Conflict
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.storage.filters import (
    StorageMediumFilter,
    StorageMethodFilter,
)
from ESSArch_Core.storage.models import (
    STORAGE_TARGET_STATUS_ENABLED,
    TAPE,
    AccessQueue,
    IOQueue,
    Robot,
    RobotQueue,
    StorageMedium,
    StorageMethod,
    StorageMethodTargetRelation,
    StorageObject,
    StorageTarget,
    TapeDrive,
    TapeSlot,
)
from ESSArch_Core.storage.serializers import (
    AccessQueueSerializer,
    IOQueueSerializer,
    IOQueueWriteSerializer,
    RobotQueueSerializer,
    RobotSerializer,
    StorageMediumSerializer,
    StorageMigrationCreateSerializer,
    StorageObjectSerializer,
    TapeDriveSerializer,
    TapeSlotSerializer,
)
from ESSArch_Core.util import parse_content_range_header
from ESSArch_Core.WorkflowEngine.models import ProcessTask
from ESSArch_Core.WorkflowEngine.serializers import (
    ProcessTaskDetailSerializer,
    ProcessTaskSerializer,
)


class IOQueueViewSet(viewsets.ModelViewSet):
    """
    API endpoint for IO queues
    """
    queryset = IOQueue.objects.all()

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return IOQueueSerializer

        return IOQueueWriteSerializer

    @action(detail=False, methods=['post'], url_path='from-master')
    def from_master(self, request, pk=None):
        try:
            entry_data = request.data.pop('entry')
        except KeyError:
            raise exceptions.ParseError(detail='entry parameter missing')

        try:
            ip_data = request.data.pop('information_package')
        except KeyError:
            raise exceptions.ParseError(detail='information_package parameter missing')

        try:
            policy_data = ip_data.pop('policy')

            try:
                cache_storage_data = policy_data.pop('cache_storage')
                cache_storage_data.pop('url')
                cache_storage, _ = Path.objects.get_or_create(
                    entity=cache_storage_data.pop('entity'), defaults=cache_storage_data
                )
                policy_data['cache_storage'] = cache_storage
            except KeyError:
                raise exceptions.ParseError(detail='information_package.policy.cache_storage parameter missing')

            try:
                ingest_path_data = policy_data.pop('ingest_path')
                ingest_path_data.pop('url')
                ingest_path, _ = Path.objects.get_or_create(
                    entity=ingest_path_data.pop('entity'), defaults=ingest_path_data
                )
                policy_data['ingest_path'] = ingest_path
            except KeyError:
                raise exceptions.ParseError(detail='information_package.policy.ingest_path parameter missing')

            policy_data.pop('url', None)

            policy, _ = StoragePolicy.objects.update_or_create(
                id=policy_data.pop('id'), defaults=policy_data
            )

            ip_data['policy'] = policy

        except KeyError:
            raise exceptions.ParseError(detail='information_package.policy parameter missing')

        try:
            aic_data = ip_data['aic']
            aic_data.pop('url', None)
            aic, _ = InformationPackage.objects.get_or_create(
                id=aic_data.pop('id'), defaults=aic_data
            )
            ip_data['aic'] = aic

        except KeyError:
            aic = None

        ip, _ = InformationPackage.objects.get_or_create(
            id=ip_data['id'], defaults=ip_data
        )

        entry_data['ip'] = ip

        try:
            user_data = entry_data.pop('user')
            user_data.pop('url', None)
            user_data.pop('id', None)
            user, _ = User.objects.get_or_create(
                username=user_data['username'], defaults=user_data
            )
            entry_data['user'] = user
        except KeyError:
            raise exceptions.ParseError(detail='entry.user parameter missing')

        try:
            storage_method_target_data = entry_data.pop('storage_method_target')

            try:
                storage_method_data = storage_method_target_data.pop('storage_method')
                storage_method_data['storage_policy'] = policy
                storage_method_data.pop('url', None)
                storage_method, _ = StorageMethod.objects.get_or_create(
                    id=storage_method_data['id'], defaults=storage_method_data
                )
                storage_method_target_data['storage_method'] = storage_method
            except KeyError:
                raise exceptions.ParseError(detail='entry.storage_method_target.storage_method parameter missing')

            try:
                storage_target_data = storage_method_target_data.pop('storage_target')
                storage_target_data.pop('url', None)
                storage_target_data.pop('remote_server', None)
                storage_target, _ = StorageTarget.objects.get_or_create(
                    id=storage_target_data['id'], defaults=storage_target_data
                )
                storage_method_target_data['storage_target'] = storage_target
            except KeyError:
                raise exceptions.ParseError(detail='entry.storage_method_target.storage_target parameter missing')

            storage_method_target_data.pop('url', None)
            storage_method_target, _ = StorageMethodTargetRelation.objects.get_or_create(
                id=storage_method_target_data['id'], defaults=storage_method_target_data
            )
            entry_data['storage_method_target'] = storage_method_target
        except KeyError:
            raise exceptions.ParseError(detail='entry.storage_method_target parameter missing')

        entry_data['status'] = -1
        io_obj, _ = IOQueue.objects.get_or_create(id=entry_data.pop('id'), defaults=entry_data)

        return Response(io_obj.id, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='add-file')
    def add_file(self, request, pk=None):
        entry = self.get_object()

        if entry.ip.responsible != self.request.user and not request.user.has_perm('ip.can_receive_remote_files'):
            raise exceptions.PermissionDenied

        path = entry.ip.policy.cache_storage.value

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

    @action(detail=True, methods=['post'], url_path='add-file_complete')
    def add_file_complete(self, request, pk=None):
        entry = self.get_object()

        if entry.ip.responsible != self.request.user and not request.user.has_perm('ip.can_receive_remote_files'):
            raise exceptions.PermissionDenied

        path = entry.ip.policy.cache_storage.value

        md5 = request.data['md5']
        filepath = request.data['path']
        filepath = os.path.join(path, filepath)

        ProcessTask.objects.create(
            name="ESSArch_Core.tasks.ValidateIntegrity",
            params={
                "filename": filepath,
                "checksum": md5,
                "algorithm": 'MD5'
            },
            responsible=self.request.user,
        ).run().get()

        return Response('Upload of %s complete' % filepath)

    @action(detail=True, methods=['post'], url_path='all-files-done')
    def all_files_done(self, request, pk=None):
        entry = self.get_object()
        entry.status = 0
        entry.save(update_fields=['status'])

        entry.ip.cached = True
        entry.ip.save(update_fields=['cached'])
        return Response()


class StorageMediumViewSet(viewsets.ModelViewSet):
    """
    API endpoint for storage medium
    """
    queryset = StorageMedium.objects.all()
    serializer_class = StorageMediumSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter)

    filterset_class = StorageMediumFilter

    search_fields = (
        '=id', 'medium_id', 'status', 'location', 'location_status', 'used_capacity', 'create_date',
    )
    ordering = ('-create_date',)

    @action(detail=True, methods=['post'])
    def mount(self, request, pk=None):
        medium = self.get_object()

        if medium.get_type() != TAPE:
            raise exceptions.ParseError('%s is not a tape' % medium)

        if medium.tape_drive is not None:
            raise Conflict(detail='Tape already mounted')

        RobotQueue.objects.get_or_create(
            user=self.request.user,
            storage_medium=medium,
            req_type=10, status__in=[0, 2], defaults={'status': 0}
        )

        return Response(status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'])
    def unmount(self, request, pk=None):
        medium = self.get_object()

        if medium.tape_drive is None:
            raise exceptions.ParseError(detail='Tape not mounted')

        force = request.data.get('force', False)
        req_type = 30 if force else 20

        RobotQueue.objects.get_or_create(
            user=self.request.user,
            storage_medium=medium,
            req_type=req_type, status__in=[0, 2], defaults={'status': 0}
        )

        return Response(status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        medium: StorageMedium = self.get_object()

        if medium.status == 0:
            raise exceptions.ParseError('{} is already deactivated'.format(medium.medium_id))

        if not medium.is_migrated():
            raise exceptions.ParseError('{} is not fully migrated yet'.format(medium.medium_id))

        medium.deactivate()
        return Response(status=status.HTTP_200_OK)


class StorageMethodViewSet(viewsets.ModelViewSet):
    """
    API endpoint for storage method
    """
    queryset = StorageMethod.objects.all()
    serializer_class = StorageMethodSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter,)
    filterset_class = StorageMethodFilter
    search_fields = ('name',)


class StorageMethodTargetRelationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for storage method target relation
    """
    queryset = StorageMethodTargetRelation.objects.all()
    serializer_class = StorageMethodTargetRelationSerializer


class StorageObjectViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoint for storage object
    """
    queryset = StorageObject.objects.all()
    serializer_class = StorageObjectSerializer

    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend, SearchFilter,
    )
    ordering_fields = (
        'ip__object_identifier_value', 'content_location_value', 'last_changed_local',
    )

    search_fields = (
        'ip__object_identifier_value', 'content_location_value',
    )


class StorageTargetViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoint for storage target
    """
    queryset = StorageTarget.objects.all()
    serializer_class = StorageTargetSerializer

    filter_backends = (DjangoFilterBackend, SearchFilter)
    filterset_fields = ('status', 'type',)
    search_fields = ('name',)

    def get_queryset(self):
        parents_query_dict = self.get_parents_query_dict()
        ip_id = parents_query_dict.get('ip')
        if ip_id is None:
            return self.queryset

        ip = InformationPackage.objects.get(pk=ip_id)
        storage_methods = ip.get_migratable_storage_methods()
        return StorageTarget.objects.filter(
            storage_method_target_relations__status=STORAGE_TARGET_STATUS_ENABLED,
            storage_method_target_relations__storage_method__in=storage_methods,
        )


class RobotViewSet(viewsets.ModelViewSet):
    """
    API endpoint for robot
    """
    queryset = Robot.objects.all()
    serializer_class = RobotSerializer
    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend, SearchFilter,
    )
    ordering_fields = (
        'id', 'label', 'device', 'online',
    )

    search_fields = (
        '=id', 'label', 'device', 'online',
    )

    @action(detail=True, methods=['post'])
    def inventory(self, request, pk=None):
        robot = self.get_object()

        t = ProcessTask.objects.create(
            name='ESSArch_Core.tasks.RobotInventory',
            args=[robot.device],
            eager=False,
            responsible=self.request.user,
        )
        t.run()
        t_id = str(t.pk)

        return Response({'detail': 'Running robot inventory: {}'.format(t_id)}, status=status.HTTP_202_ACCEPTED)


class AccessQueueViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoint for access queue
    """
    queryset = AccessQueue.objects.all()
    serializer_class = AccessQueueSerializer
    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend, SearchFilter,
    )
    ordering_fields = ('posted',)


class RobotQueueViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoint for robot
    """
    queryset = RobotQueue.objects.all()
    serializer_class = RobotQueueSerializer
    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend, SearchFilter,
    )
    ordering_fields = (
        'id', 'user', 'posted', 'robot', 'io_queue_entry',
        'storage_medium', 'req_type', 'status',
    )

    search_fields = (
        '=id', 'user__username', 'posted', 'robot__label',
        'storage_medium__medium_id', 'req_type', 'status',
    )


class TapeDriveViewSet(viewsets.ModelViewSet):
    """
    API endpoint for TapeDrive
    """
    queryset = TapeDrive.objects.all()
    serializer_class = TapeDriveSerializer
    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend, SearchFilter,
    )
    ordering_fields = (
        'id', 'device', 'num_of_mounts', 'idle_time',
    )
    search_fields = (
        '=id', 'device', 'num_of_mounts', 'idle_time',
    )

    @action(detail=True, methods=['post'])
    def mount(self, request, pk=None):
        drive = self.get_object()

        try:
            storage_medium = StorageMedium.objects.get(pk=request.data['storage_medium'])
        except KeyError:
            raise exceptions.ParseError('Missing parameter storage_medium')
        except StorageMedium.DoesNotExist:
            raise exceptions.ParseError('Invalid storage_medium')

        if storage_medium.get_type() != TAPE:
            raise exceptions.ParseError('%s is not a tape' % storage_medium)

        RobotQueue.objects.get_or_create(
            user=self.request.user,
            storage_medium_id=storage_medium,
            tape_drive=drive,
            req_type=10, status__in=[0, 2], defaults={'status': 0}
        )

        return Response()

    @action(detail=True, methods=['post'])
    def unmount(self, request, pk=None):
        drive = self.get_object()
        force = request.data.get('force', False)

        req_type = 30 if force else 20

        if not hasattr(drive, 'storage_medium'):
            raise exceptions.ParseError(detail='No tape mounted')

        RobotQueue.objects.get_or_create(
            user=self.request.user,
            storage_medium=drive.storage_medium,
            req_type=req_type, status__in=[0, 2], defaults={'status': 0}
        )

        return Response()


class TapeSlotViewSet(viewsets.ModelViewSet):
    """
    API endpoint for TapeSlot
    """
    queryset = TapeSlot.objects.all()
    serializer_class = TapeSlotSerializer
    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend, SearchFilter,
    )
    ordering_fields = (
        'id', 'slot_id', 'medium_id',
    )
    search_fields = (
        '=id', 'slot_id', 'medium_id', 'status'
    )


class StorageMigrationViewSet(viewsets.ModelViewSet):
    queryset = ProcessTask.objects.filter(name='ESSArch_Core.storage.tasks.StorageMigration')
    filter_backends = (SearchFilter,)
    search_fields = (
        'label', 'information_package__id', 'information_package__object_identifier_value',
        'information_package__label',
    )

    def get_serializer_class(self):
        if self.action == 'create':
            return StorageMigrationCreateSerializer

        if self.action == 'list':
            return ProcessTaskSerializer

        return ProcessTaskDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {'detail': 'Migration jobs created and queued'},
            status=status.HTTP_201_CREATED, headers=headers,
        )
