import logging
import os

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from rest_framework import serializers, validators

from ESSArch_Core.api.serializers import DynamicModelSerializer
from ESSArch_Core.auth.serializers import UserSerializer
from ESSArch_Core.configuration.models import Path, StoragePolicy
from ESSArch_Core.configuration.serializers import StorageTargetSerializer
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.ip.serializers import (
    InformationPackageDetailSerializer,
    InformationPackageSerializer,
)
from ESSArch_Core.storage.models import (
    DISK,
    STORAGE_TARGET_STATUS_ENABLED,
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
from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask


class StorageMediumSerializer(serializers.ModelSerializer):
    storage_target = StorageTargetSerializer(allow_null=False, required=True)
    tape_drive = serializers.PrimaryKeyRelatedField(
        pk_field=serializers.UUIDField(format='hex_verbose'),
        allow_null=True,
        required=False,
        queryset=TapeDrive.objects.all()
    )
    tape_slot = serializers.PrimaryKeyRelatedField(
        pk_field=serializers.UUIDField(format='hex_verbose'),
        allow_null=True,
        required=False,
        queryset=TapeSlot.objects.all()
    )
    status_display = serializers.SerializerMethodField()
    location_status_display = serializers.SerializerMethodField()
    block_size_display = serializers.SerializerMethodField()
    format_display = serializers.SerializerMethodField()

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_location_status_display(self, obj):
        return obj.get_location_status_display()

    def get_format_display(self, obj):
        return obj.get_format_display()

    def get_block_size_display(self, obj):
        return obj.get_block_size_display()

    class Meta:
        model = StorageMedium
        fields = (
            'id', 'medium_id', 'status', 'status_display', 'location', 'location_status',
            'location_status_display', 'block_size', 'block_size_display', 'format', 'format_display',
            'used_capacity', 'num_of_mounts', 'create_date',
            'agent', 'storage_target', 'tape_slot', 'tape_drive',
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'validators': [],
            },
            'medium_id': {
                'validators': [],
            },
        }


class StorageMediumWriteSerializer(StorageMediumSerializer):
    storage_target = serializers.PrimaryKeyRelatedField(
        pk_field=serializers.UUIDField(format='hex_verbose'),
        allow_null=False,
        required=True,
        queryset=StorageTarget.objects.all()
    )

    def create(self, validated_data):
        obj, _ = StorageMedium.objects.update_or_create(id=validated_data['id'], defaults=validated_data)

        return obj


class StorageObjectListSerializer(serializers.ListSerializer):
    def update(self, instance, validated_data):
        ret = []

        for data in validated_data:
            obj, _ = StorageObject.objects.update_or_create(id=data['id'], defaults=data)
            ret.append(obj)
        return ret


class StorageObjectSerializer(serializers.ModelSerializer):
    content_location_value_display = serializers.SerializerMethodField()
    ip = serializers.PrimaryKeyRelatedField(
        pk_field=serializers.UUIDField(format='hex_verbose'),
        allow_null=True,
        required=False,
        queryset=InformationPackage.objects.all()
    )
    medium_id = serializers.CharField(source='storage_medium.medium_id')
    target_name = serializers.CharField(source='storage_medium.storage_target.name')
    target_target = serializers.CharField(source='storage_medium.storage_target.target')
    storage_medium = serializers.PrimaryKeyRelatedField(
        pk_field=serializers.UUIDField(format='hex_verbose'),
        allow_null=True,
        required=False,
        queryset=StorageMedium.objects.all()
    )
    ip_object_identifier_value = serializers.CharField(source='ip.object_identifier_value', read_only=True)
    ip_object_size = serializers.CharField(source='ip.object_size', read_only=True)

    def get_content_location_value_display(self, obj):
        if obj.content_location_type == DISK:
            return os.path.join(obj.storage_medium.storage_target.target, obj.content_location_value)
        return obj.content_location_value

    def create(self, validated_data):
        obj, _ = StorageObject.objects.update_or_create(id=validated_data['id'], defaults=validated_data)

        return obj

    class Meta:
        model = StorageObject
        list_serializer_class = StorageObjectListSerializer
        fields = (
            'id', 'content_location_type', 'content_location_value', 'content_location_value_display',
            'last_changed_local', 'last_changed_external', 'ip', 'medium_id', 'target_name', 'target_target',
            'storage_medium', 'container', 'ip_object_identifier_value', 'ip_object_size',
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'validators': [],
            },
        }


class StorageObjectNestedSerializer(StorageObjectSerializer):
    storage_medium = StorageMediumSerializer()


class StorageObjectWithIPSerializer(StorageObjectSerializer):
    ip = InformationPackageSerializer(read_only=True)


class RobotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Robot
        fields = (
            'id', 'label', 'device', 'online',
        )


class TapeSlotSerializer(serializers.ModelSerializer):
    storage_medium = StorageMediumSerializer()
    locked = serializers.SerializerMethodField()
    mounted = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_locked(self, obj):
        if hasattr(obj, 'storage_medium') and obj.storage_medium.tape_drive is not None:
            return obj.storage_medium.tape_drive.locked
        return False

    def get_mounted(self, obj):
        return hasattr(obj, 'storage_medium') and obj.storage_medium.tape_drive is not None

    class Meta:
        model = TapeSlot
        fields = (
            'id', 'slot_id', 'medium_id', 'robot', 'status', 'status_display', 'locked', 'mounted',
            'storage_medium',
        )


class TapeDriveSerializer(serializers.ModelSerializer):
    storage_medium = StorageMediumSerializer(read_only=True)
    status_display = serializers.SerializerMethodField()
    idle_timer = serializers.SerializerMethodField()
    locked = serializers.SerializerMethodField()

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_idle_timer(self, obj):
        try:
            obj.storage_medium
        except TapeDrive.storage_medium.RelatedObjectDoesNotExist:
            return 0
        idle_timer_seconds = (obj.last_change - (timezone.now() - obj.idle_time)).total_seconds()
        if idle_timer_seconds < 0:
            return 0
        return int(idle_timer_seconds)

    def get_locked(self, obj):
        if obj.locked or obj.is_locked():
            return True
        else:
            return False

    class Meta:
        model = TapeDrive
        fields = (
            'id', 'drive_id', 'device', 'io_queue_entry', 'num_of_mounts', 'idle_time', 'idle_timer', 'robot',
            'status', 'status_display', 'storage_medium', 'locked', 'last_change',
        )


class IOQueueSerializer(DynamicModelSerializer):
    ip = InformationPackageDetailSerializer()
    result = serializers.ModelField(model_field=IOQueue()._meta.get_field('result'), read_only=False)
    user = UserSerializer()
    storage_method_target = serializers.PrimaryKeyRelatedField(
        pk_field=serializers.UUIDField(format='hex_verbose'),
        allow_null=True,
        queryset=StorageMethodTargetRelation.objects.all()
    )
    storage_medium = serializers.PrimaryKeyRelatedField(
        pk_field=serializers.UUIDField(format='hex_verbose'),
        allow_null=True,
        queryset=StorageMedium.objects.all()
    )
    storage_object = StorageObjectNestedSerializer(allow_null=True, required=False)

    req_type_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    def get_req_type_display(self, obj):
        return obj.get_req_type_display()

    def get_status_display(self, obj):
        return obj.get_status_display()

    class Meta:
        model = IOQueue
        fields = (
            'id', 'req_type', 'req_type_display', 'req_purpose', 'user', 'object_path',
            'write_size', 'result', 'status', 'status_display', 'task_id', 'posted',
            'ip', 'storage_method_target', 'storage_medium', 'storage_object', 'access_queue',
            'remote_status', 'transfer_task_id'
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'validators': [validators.UniqueValidator(queryset=IOQueue.objects.all())],
            },
        }


class IOQueueWriteSerializer(IOQueueSerializer):
    storage_method_target = serializers.UUIDField(required=True)
    storage_medium = serializers.UUIDField(allow_null=True, required=False)

    def create(self, validated_data):
        ip_data = validated_data.pop('ip')
        aic_data = ip_data.pop('aic')
        policy_data = ip_data.pop('policy')
        storage_method_set_data = policy_data.pop('storage_methods')

        storage_object_data = validated_data.pop('storage_object', None)

        if storage_object_data is not None:
            storage_object = StorageObject.objects.get(pk=storage_object_data.get('id'))
        else:
            storage_object = None

        validated_data['storage_object'] = storage_object

        cache_storage_data = policy_data.pop('cache_storage')
        ingest_path_data = policy_data.pop('ingest_path')

        cache_storage = Path.objects.get_or_create(entity=cache_storage_data['entity'], defaults=cache_storage_data)
        ingest_path = Path.objects.get_or_create(entity=ingest_path_data['entity'], defaults=ingest_path_data)

        policy_data['cache_storage'], _ = cache_storage
        policy_data['ingest_path'], _ = ingest_path

        policy, _ = StoragePolicy.objects.update_or_create(policy_id=policy_data['policy_id'],
                                                           defaults=policy_data)

        for storage_method_data in storage_method_set_data:
            storage_method_target_set_data = storage_method_data.pop('storage_method_target_relations')
            storage_method_data['storage_policy'] = policy
            storage_method, _ = StorageMethod.objects.update_or_create(
                id=storage_method_data['id'],
                defaults=storage_method_data
            )

            for storage_method_target_data in storage_method_target_set_data:
                storage_target_data = storage_method_target_data.pop('storage_target')
                storage_target, _ = StorageTarget.objects.update_or_create(
                    id=storage_target_data['id'],
                    defaults=storage_target_data
                )
                storage_method_target_data['storage_method'] = storage_method
                storage_method_target_data['storage_target'] = storage_target
                storage_method_target, _ = StorageMethodTargetRelation.objects.update_or_create(
                    id=storage_method_target_data['id'],
                    defaults=storage_method_target_data
                )

        aic, _ = InformationPackage.objects.get_or_create(id=aic_data['id'], defaults=aic_data)

        user = None
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            user = get_user_model.objects.get(username="system")

        validated_data['user'] = user

        ip_data['aic'] = aic
        ip_data['policy'] = policy
        ip_data['responsible'] = user
        ip, _ = InformationPackage.objects.get_or_create(id=ip_data['id'], defaults=ip_data)

        storage_method_target = StorageMethodTargetRelation.objects.get(id=validated_data.pop('storage_method_target'))

        try:
            storage_medium_data = validated_data.pop('storage_medium')

            if storage_medium_data is not None:
                storage_medium = StorageMedium.objects.get(id=storage_medium_data)
            else:
                storage_medium = None
        except (KeyError, StorageMedium.DoesNotExist):
            storage_medium = None

        return IOQueue.objects.create(ip=ip, storage_method_target=storage_method_target,
                                      storage_medium=storage_medium, **validated_data)

    def update(self, instance, validated_data):
        storage_object_data = validated_data.pop('storage_object', None)

        user = None
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        else:
            user = get_user_model.objects.get(username="system")

        if storage_object_data is not None:
            storage_medium_data = storage_object_data.pop('storage_medium')
            storage_medium_data['agent'] = user
            storage_medium_data['last_changed_local'] = timezone.now
            storage_medium, _ = StorageMedium.objects.update_or_create(
                id=storage_medium_data['id'],
                defaults=storage_medium_data
            )

            storage_object_data['storage_medium'] = storage_medium
            storage_object_data['last_changed_local'] = timezone.now
            storage_object, _ = StorageObject.objects.update_or_create(
                id=storage_object_data['id'],
                defaults=storage_object_data
            )

            instance.storage_object = storage_object

        storage_medium_data = validated_data.pop('storage_medium', None)

        try:
            instance.storage_medium = StorageMedium.objects.get(id=storage_medium_data)
        except StorageMedium.DoesNotExist:
            if storage_medium_data is not None:
                raise

        instance.result = validated_data.get('result', instance.result)
        instance.status = validated_data.get('status', instance.status)

        instance.save()

        return instance


class AccessQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessQueue
        fields = (
            'id', 'user', 'posted', 'ip', 'package', 'extracted',
            'new', 'object_identifier_value', 'new_ip', 'status',
        )


class RobotQueueSerializer(serializers.ModelSerializer):
    io_queue_entry = IOQueueSerializer(read_only=True)
    robot = RobotSerializer(read_only=True)
    storage_medium = StorageMediumSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    req_type = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_req_type(self, obj):
        return obj.get_req_type_display()

    def get_status(self, obj):
        return obj.get_status_display()

    class Meta:
        model = RobotQueue
        fields = (
            'id', 'user', 'posted', 'robot', 'io_queue_entry',
            'storage_medium', 'req_type', 'status'
        )


class InformationPackagePolicyField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        policy = self.context['policy']
        return InformationPackage.objects.filter(submission_agreement__policy=policy)


class StorageMethodPolicyField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        policy = self.context['policy']
        return StorageMethod.objects.filter_has_target_with_status(
            STORAGE_TARGET_STATUS_ENABLED, True,
        ).filter(storage_policies=policy)


class StorageMigrationCreateSerializer(serializers.Serializer):
    information_packages = InformationPackagePolicyField(write_only=True, many=True, required=False)
    storage_mediums = serializers.PrimaryKeyRelatedField(
        write_only=True, many=True, required=False, queryset=StorageMedium.objects.all()
    )
    policy = serializers.PrimaryKeyRelatedField(write_only=True, queryset=StoragePolicy.objects.all())
    storage_methods = StorageMethodPolicyField(write_only=True, many=True, required=False)
    temp_path = serializers.CharField(write_only=True)
    export_path = serializers.CharField(write_only=True, required=False, allow_blank=True)
    include_inactive_ips = serializers.BooleanField(write_only=True, required=False, default=False)
    missing_storage = serializers.BooleanField(write_only=True, required=False, default=False)

    def create(self, validated_data):
        logger = logging.getLogger('essarch')
        steps = []
        user = None
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
        storage_methods = validated_data.get('storage_methods', [])
        export_path = validated_data.get('export_path', '')
        include_inactive_ips = validated_data.get('include_inactive_ips', '')
        missing_storage = validated_data.get('missing_storage', '')
        if isinstance(storage_methods, list):
            storage_methods = StorageMethod.objects.filter(
                pk__in=[s.pk for s in storage_methods]
            )
        with transaction.atomic():
            if validated_data.get('information_packages', False):
                medium_ids = {}
                num_of_ip_with_storage = 0
                for storage_obj in StorageObject.objects.filter(
                    pk__in=InformationPackage.objects.filter(
                        pk__in=[ip.pk for ip in validated_data['information_packages']]
                    ).annotate(
                        fastest=Subquery(
                            StorageObject.objects.filter(
                                ip=OuterRef('pk'),
                            ).readable().fastest().values('pk')[:1]
                        )
                    ).values('fastest')
                ).select_related('ip').readable().fastest():
                    if storage_obj.storage_medium.medium_id not in medium_ids.keys():
                        medium_ids[storage_obj.storage_medium.medium_id] = []
                    medium_ids[storage_obj.storage_medium.medium_id].append(storage_obj.ip)
                    num_of_ip_with_storage += 1
                if len(validated_data['information_packages']) != num_of_ip_with_storage:
                    raise serializers.ValidationError(
                        'Missing storage for some IP in: {}'.format(validated_data['information_packages']))

                for medium_id in medium_ids.keys():
                    media_migrate_workflow_step = ProcessStep.objects.create(
                        name='Migrate Storage Medium', eager=False, information_package=None, context={},
                        responsible=user, label='Migrate Storage Medium {}'.format(medium_id),
                        part_root=None, run_state='')

                    t = ProcessTask.objects.create(
                        name='ESSArch_Core.storage.tasks.CreateMediumMigrationWorkflow',
                        params={
                            'media_migrate_workflow_step_id': media_migrate_workflow_step.pk,
                            'ip_ids': [ip.pk for ip in medium_ids[medium_id]],
                            'storage_method_ids': [s.pk for s in storage_methods],
                            'temp_path': validated_data['temp_path'],
                            'export_path': export_path,
                        },
                        eager=False,
                        responsible=user,
                    )
                    t.run()
                    logger.info('Created task {} for medium {} with {} IPs'.format(
                        t.id, medium_id, len(medium_ids[medium_id])))
                    steps.append(media_migrate_workflow_step)

                return ProcessStep.objects.filter(pk__in=[s.pk for s in steps])

            elif validated_data.get('storage_mediums', False):
                for StorageMedium_obj in StorageMedium.objects.filter(
                        pk__in=[s.pk for s in validated_data['storage_mediums']]).natural_sort():
                    ip_ids_sorted_for_medium = list(StorageMedium_obj.storage.all().natural_sort().values_list(
                        'ip', flat=True))
                    ip_objs_migratable_bulk = InformationPackage.objects.migratable(
                        export_path=export_path, missing_storage=missing_storage, storage_methods=storage_methods,
                        include_inactive_ips=include_inactive_ips).filter(
                            pk__in=StorageMedium_obj.storage.all().natural_sort().values_list('ip', flat=True)
                    ).in_bulk()
                    ip_objs_migratable_sorted = [
                        ip_objs_migratable_bulk[id] for id in ip_ids_sorted_for_medium
                        if id in ip_objs_migratable_bulk]
                    information_packages = ip_objs_migratable_sorted

                    media_migrate_workflow_step = ProcessStep.objects.create(
                        name='Migrate Storage Medium', eager=False, information_package=None, context={},
                        responsible=user, label='Migrate Storage Medium {}'.format(StorageMedium_obj.medium_id),
                        part_root=None, run_state='')

                    t = ProcessTask.objects.create(
                        name='ESSArch_Core.storage.tasks.CreateMediumMigrationWorkflow',
                        params={
                            'media_migrate_workflow_step_id': media_migrate_workflow_step.pk,
                            'ip_ids': [ip.pk for ip in information_packages],
                            'storage_method_ids': [s.pk for s in storage_methods],
                            'temp_path': validated_data['temp_path'],
                            'export_path': export_path,
                        },
                        eager=False,
                        responsible=user,
                    )
                    t.run()
                    logger.info('Created task {} for medium {} with {} IPs'.format(
                        t.id, StorageMedium_obj.medium_id, len(information_packages)))
                    steps.append(media_migrate_workflow_step)

                return ProcessStep.objects.filter(pk__in=[s.pk for s in steps])

    class Meta:
        model = None


class StorageMigrationPreviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = InformationPackage
        fields = ('id', 'label', 'object_identifier_value',)


class StorageMigrationPreviewWriteSerializer(serializers.Serializer):
    information_packages = InformationPackagePolicyField(write_only=True, many=True, required=False)
    storage_mediums = serializers.PrimaryKeyRelatedField(
        write_only=False, many=True, required=False, queryset=StorageMedium.objects.all()
    )
    policy = serializers.PrimaryKeyRelatedField(write_only=True, queryset=StoragePolicy.objects.all())
    storage_methods = StorageMethodPolicyField(write_only=True, many=True, required=False)
    export_path = serializers.CharField(write_only=True, required=False, allow_blank=True)
    include_inactive_ips = serializers.BooleanField(write_only=True, required=False, default=False)
    missing_storage = serializers.BooleanField(write_only=True, required=False, default=False)

    def create(self, validated_data):
        information_packages = validated_data['information_packages']
        policy = validated_data['policy']
        storage_methods = validated_data['storage_methods']
        export_path = validated_data.get('export_path', '')
        include_inactive_ips = validated_data.get('include_inactive_ips', '')
        missing_storage = validated_data.get('missing_storage', '')
        if isinstance(storage_methods, list):
            storage_methods = StorageMethod.objects.filter(
                pk__in=[s.pk for s in storage_methods]
            )

        if validated_data.get('storage_mediums', False) and information_packages == []:
            information_packages = []
            for StorageMedium_obj in StorageMedium.objects.filter(
                    pk__in=[s.pk for s in validated_data['storage_mediums']]).readable():
                ip_ids_sorted_for_medium = list(StorageMedium_obj.storage.all().natural_sort().values_list(
                    'ip', flat=True))
                ip_objs_migratable_bulk = InformationPackage.objects.migratable(
                    export_path=export_path, missing_storage=missing_storage, storage_methods=storage_methods,
                    policy=policy, include_inactive_ips=include_inactive_ips).filter(
                        pk__in=StorageMedium_obj.storage.all().natural_sort().values_list('ip', flat=True)
                ).in_bulk()
                ip_objs_migratable_sorted = [
                    ip_objs_migratable_bulk[id] for id in ip_ids_sorted_for_medium if id in ip_objs_migratable_bulk]
                information_packages.extend(ip_objs_migratable_sorted)

        if validated_data.get('information_packages', False) and not validated_data.get('storage_mediums', False):
            information_packages = []
            for storage_obj in StorageObject.objects.filter(
                pk__in=InformationPackage.objects.filter(
                    pk__in=[ip.pk for ip in validated_data['information_packages']]
                ).annotate(
                    fastest=Subquery(
                        StorageObject.objects.filter(
                            ip=OuterRef('pk'),
                        ).readable().fastest().values('pk')[:1]
                    )
                ).values('fastest')
            ).select_related('ip').readable().fastest():
                information_packages.append(storage_obj.ip)

        return StorageMigrationPreviewSerializer(instance=information_packages, many=True).data


class StorageMigrationPreviewDetailWriteSerializer(serializers.Serializer):
    policy = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=StoragePolicy.objects.all(),
    )
    storage_methods = StorageMethodPolicyField(
        write_only=True, many=True, required=False,
    )
    export_path = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def create(self, validated_data):
        ip = validated_data['information_package']
        storage_methods = validated_data['storage_methods']
        export_path = validated_data.get('export_path', '')

        if isinstance(storage_methods, list):
            storage_methods = StorageMethod.objects.filter(
                pk__in=[s.pk for s in storage_methods]
            )

        storage_methods = storage_methods.filter(pk__in=ip.get_migratable_storage_methods())

        targets = StorageTarget.objects.filter(
            storage_method_target_relations__storage_method__in=storage_methods,
            storage_method_target_relations__status=STORAGE_TARGET_STATUS_ENABLED,
        )
        data = StorageTargetSerializer(instance=targets, many=True).data
        if export_path:
            data.append({"id": 'export', "name": export_path})
        return data
