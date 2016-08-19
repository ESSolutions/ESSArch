from django.contrib.auth.models import User, Group

from rest_framework import serializers

from preingest.models import ArchiveObject, Event, EventType, ProcessStep, ProcessTask

class PickledObjectField(serializers.Field):
    def to_representation(self, obj):
        return obj

    def to_internal_value(self, data):
        return data

class ArchiveObjectSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ArchiveObject
        fields = ('url', 'ObjectUUID', 'label', 'steps', 'events',)

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
            'undone',
        )

        read_only_fields = (
            'celery_id', 'progress', 'status', 'time_started', 'time_done', 'undone',
        )

    params = serializers.JSONField()

class EventSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Event
        fields = (
            'url', 'id', 'type', 'dateTime', 'detail', 'application',
            'version', 'outcome', 'outcomeDetailNote',
            'linkingAgentIdentifierValue', 'archiveObject',
        )

        read_only_fields = ('eventDateTime',)

class EventTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EventType
        fields = ('url', 'id', 'code', 'desc_sv', 'desc_en',)

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')
