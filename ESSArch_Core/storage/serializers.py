import os

from django.contrib.auth import get_user_model
from rest_framework import serializers, validators

from ESSArch_Core.api.serializers import DynamicModelSerializer
from ESSArch_Core.auth.serializers import UserSerializer
from ESSArch_Core.configuration.models import Path, StoragePolicy
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.ip.serializers import (
    InformationPackageDetailSerializer,
    InformationPackageSerializer,
)
from ESSArch_Core.storage.models import (
    DISK,
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
from ESSArch_Core.WorkflowEngine.models import ProcessTask


class StorageMediumSerializer(serializers.ModelSerializer):
    storage_target = serializers.PrimaryKeyRelatedField(
        pk_field=serializers.UUIDField(format='hex_verbose'),
        allow_null=False,
        required=True,
        queryset=StorageTarget.objects.all()
    )
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
    location_status_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    def get_location_status_display(self, obj):
        return obj.get_location_status_display()

    def get_status_display(self, obj):
        return obj.get_status_display()

    class Meta:
        model = StorageMedium
        fields = (
            'id', 'medium_id', 'status', 'status_display', 'location', 'location_status',
            'location_status_display', 'block_size', 'format', 'used_capacity', 'num_of_mounts', 'create_date',
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


class StorageObjectSerializer(serializers.ModelSerializer):
    medium_id = serializers.CharField(source='storage_medium.medium_id')
    target_name = serializers.CharField(source='storage_medium.storage_target.name')
    target_target = serializers.CharField(source='storage_medium.storage_target.target')
    content_location_value = serializers.SerializerMethodField()

    def get_content_location_value(self, obj):
        if obj.content_location_type == DISK:
            return os.path.join(obj.storage_medium.storage_target.target, '%s.tar' % obj.ip.object_identifier_value)

        return obj.content_location_value

    class Meta:
        model = StorageObject
        fields = (
            'id', 'content_location_type', 'content_location_value', 'last_changed_local',
            'last_changed_external', 'ip', 'medium_id', 'target_name', 'target_target', 'storage_medium',
            'container',
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

    def get_status_display(self, obj):
        return obj.get_status_display()

    class Meta:
        model = TapeDrive
        fields = (
            'id', 'drive_id', 'device', 'io_queue_entry', 'num_of_mounts', 'idle_time', 'robot', 'status',
            'status_display', 'storage_medium', 'locked', 'last_change',
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
            storage_medium, _ = StorageMedium.objects.update_or_create(
                id=storage_medium_data['id'],
                defaults=storage_medium_data
            )

            storage_object_data['storage_medium'] = storage_medium
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
        request = self.context['request']
        qs = InformationPackage.objects.migratable()

        policy = request.data.get('policy')
        if policy is not None:
            qs = qs.filter(policy=policy)

        return qs


class StorageMigrationCreateSerializer(serializers.Serializer):
    information_packages = InformationPackagePolicyField(
        write_only=True, many=True,
        queryset=InformationPackage.objects.migratable(),
    )
    policy = serializers.PrimaryKeyRelatedField(
        queryset=StoragePolicy.objects.all(),
    )
    temp_path = serializers.CharField(write_only=True, allow_blank=False, allow_null=False)

    def create(self, validated_data):
        tasks = []
        for ip in validated_data['information_packages']:
            storage_methods = ip.get_migratable_storage_methods()
            if not storage_methods.exists():
                raise ValueError('No storage methods available for migration')

            for storage_method in storage_methods:
                t = ProcessTask(
                    name='ESSArch_Core.storage.tasks.StorageMigration',
                    label='Migrate to {}'.format(storage_method),
                    args=[str(storage_method.pk), validated_data['temp_path']],
                    information_package=ip,
                    responsible=self.context['request'].user,
                    eager=False,
                )
                tasks.append(t)

        ProcessTask.objects.bulk_create(tasks, 100)

        for t in tasks:
            t.run()

        return ProcessTask.objects.filter(pk__in=[t.pk for t in tasks])
