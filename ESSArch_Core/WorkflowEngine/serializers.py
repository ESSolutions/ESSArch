from django.contrib.auth.models import User, Group

from rest_framework import serializers

from configuration.models import EventType

from ip.models import EventIP, InformationPackage

from preingest.models import ProcessStep, ProcessTask

class PickledObjectField(serializers.Field):
    def to_representation(self, obj):
        return obj

    def to_internal_value(self, data):
        return data

class InformationPackageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = InformationPackage
        fields = (
            'url', 'id', 'Label', 'Content', 'Responsible', 'CreateDate',
            'State', 'Status', 'ObjectSize', 'ObjectNumItems', 'ObjectPath',
            'Startdate', 'Enddate', 'OAIStype', 'steps', 'events',
        )

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

class EventIPSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EventIP
        fields = (
                'url', 'id', 'eventType', 'eventDateTime', 'eventDetail',
                'eventApplication', 'eventVersion', 'eventOutcome',
                'eventOutcomeDetailNote', 'linkingAgentIdentifierValue',
                'linkingObjectIdentifierValue',
        )

class EventTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EventType
        fields = ('url', 'id', 'eventType', 'eventDetail',)

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')
