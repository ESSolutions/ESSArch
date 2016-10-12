from django.contrib.auth.models import User, Group, Permission

from rest_framework import serializers

from preingest.models import ProcessStep, ProcessTask
from preingest.util import available_tasks

import jsonpickle
import json

class PickledObjectFieldSerializer(serializers.Field):
    def to_representation(self, obj):
        return json.loads(jsonpickle.encode(obj))

    def to_internal_value(self, data):
        return jsonpickle.decode(json.dumps(data))


class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class ProcessTaskSerializer(serializers.HyperlinkedModelSerializer):
    name =  serializers.ChoiceField(
        choices=available_tasks(),
    )

    class Meta:
        model = ProcessTask
        fields = (
            'url', 'id', 'name', 'status', 'progress',
            'processstep', 'processstep_pos', 'time_started',
            'time_done', 'undone', 'undo_type', 'retried',
        )

        read_only_fields = (
            'status', 'progress', 'time_started', 'time_done', 'undone',
            'undo_type', 'retried',
        )


class ProcessTaskDetailSerializer(serializers.HyperlinkedModelSerializer):
    params = serializers.SerializerMethodField()
    result = serializers.SerializerMethodField()

    def get_params(self, obj):
        return dict((str(k), str(v)) for k,v in obj.params.iteritems())

    def get_result(self, obj):
        return str(obj.result)

    class Meta:
        model = ProcessTaskSerializer.Meta.model
        fields = ProcessTaskSerializer.Meta.fields + (
            'params', 'result', 'traceback',
        )
        read_only_fields = ProcessTaskSerializer.Meta.read_only_fields + (
            'params', 'result', 'traceback',
        )


class ProcessTaskSetSerializer(ProcessTaskSerializer):
    class Meta:
        model = ProcessTaskSerializer.Meta.model
        fields = (
            'url', 'name',
        )

class ProcessStepSerializer(serializers.HyperlinkedModelSerializer):
    tasks = ProcessTaskSerializer(many=True, read_only=True)
    task_set = ProcessTaskSetSerializer(many=True, read_only=True)
    child_steps = RecursiveField(many=True, read_only=True)

    class Meta:
        model = ProcessStep
        fields = (
            'url', 'id', 'name', 'result', 'type', 'user', 'parallel',
            'status', 'progress', 'undone', 'time_created', 'parent_step',
            'parent_step_pos', 'information_package', 'child_steps', 'tasks',
            'task_set',
        )
        read_only_fields = (
            'status', 'progress', 'time_created', 'time_done', 'undone',
        )


class PermissionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Permission
        fields = ('url', 'id', 'name', 'codename', 'group_set')


class UserSerializer(serializers.HyperlinkedModelSerializer):
    user_permissions = PermissionSerializer(many=True)

    class Meta:
        model = User
        fields = (
            'url', 'id', 'username', 'first_name', 'last_name', 'email',
            'groups', 'is_staff', 'is_active', 'is_superuser', 'last_login',
            'date_joined', 'user_permissions',
        )
        read_only_fields = (
            'last_login', 'date_joined',
        )

class GroupSerializer(serializers.HyperlinkedModelSerializer):
    permissions = PermissionSerializer(many=True)

    class Meta:
        model = Group
        fields = ('url', 'id', 'name', 'permissions', 'user_set',)
