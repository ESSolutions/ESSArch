from django.contrib.auth.models import User, Group

from rest_framework import serializers

from preingest.models import ArchiveObject, ProcessStep, ProcessTask

class PickledObjectField(serializers.Field):
    def to_representation(self, obj):
        return obj

    def to_internal_value(self, data):
        return data

class ArchiveObjectSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ArchiveObject
        fields = ('url', 'ObjectUUID', 'label',)

class ProcessStepSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProcessStep
        fields = (
            'url', 'id', 'name', 'result', 'type', 'user', 'status', 'progress',
            'time_created', 'parent_step', 'archiveobject', 'child_steps',
            'tasks', 'task_set',
        )


class ProcessTaskSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProcessTask
        fields = (
            'url', 'id', 'celery_id', 'name', 'params', 'result', 'traceback', 'status',
            'progress','processstep', 'processstep_pos', 'time_started', 'time_done',
        )

        read_only_fields = (
            'celery_id', 'progress', 'status', 'time_started', 'time_done',
        )

    params = serializers.JSONField()

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')
