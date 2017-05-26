"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Core
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

from celery import states as celery_states

from rest_framework import serializers

from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask
from ESSArch_Core.util import available_tasks


class ProcessStepChildrenSerializer(serializers.Serializer):
    url = serializers.SerializerMethodField()
    id = serializers.UUIDField()
    flow_type = serializers.SerializerMethodField()
    name = serializers.CharField()
    hidden = serializers.BooleanField()
    progress = serializers.IntegerField()
    status = serializers.CharField()
    responsible = serializers.SerializerMethodField()
    step_position = serializers.SerializerMethodField()
    time_started = serializers.DateTimeField()
    time_done = serializers.DateTimeField()

    def get_url(self, obj):
        flow_type = self.get_flow_type(obj)
        request = self.context.get('request')
        url = '/api/%ss/%s/' % (flow_type, obj.pk)
        return request.build_absolute_uri(url)

    def get_flow_type(self, obj):
        return 'task' if type(obj).__name__ == 'ProcessTask' else 'step'

    def get_responsible(self, obj):
        if type(obj).__name__ == 'ProcessTask':
            if obj.responsible:
                return obj.responsible.username
            return None
        return obj.user

    def get_step_position(self, obj):
        if type(obj).__name__ == 'ProcessTask':
            return obj.processstep_pos
        return obj.parent_step_pos


class ProcessTaskSerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.ChoiceField(
        choices=available_tasks(),
    )
    responsible = serializers.SlugRelatedField(
        slug_field='username', read_only=True
    )

    class Meta:
        model = ProcessTask
        fields = (
            'url', 'id', 'name', 'status', 'progress',
            'processstep', 'processstep_pos', 'time_started',
            'time_done', 'undone', 'undo_type', 'retried',
            'responsible', 'hidden',
        )

        read_only_fields = (
            'status', 'progress', 'time_started', 'time_done', 'undone',
            'undo_type', 'retried', 'hidden',
        )


class ProcessTaskDetailSerializer(ProcessTaskSerializer):
    args = serializers.SerializerMethodField()
    params = serializers.SerializerMethodField()
    result = serializers.SerializerMethodField()

    def get_args(self, obj):
        return obj.args

    def get_params(self, obj):
        return dict((unicode(k), unicode(v)) for k, v in obj.params.iteritems())

    def get_result(self, obj):
        return str(obj.result)

    class Meta:
        model = ProcessTaskSerializer.Meta.model
        fields = ProcessTaskSerializer.Meta.fields + (
            'args', 'params', 'result', 'traceback', 'exception',
        )
        read_only_fields = ProcessTaskSerializer.Meta.read_only_fields + (
            'args', 'params', 'result', 'traceback', 'exception',
        )


class ProcessTaskSetSerializer(ProcessTaskSerializer):
    class Meta:
        model = ProcessTaskSerializer.Meta.model
        fields = (
            'url', 'name',
        )


class ProcessStepSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProcessStep
        fields = (
            'url', 'id', 'name', 'result', 'type', 'user', 'parallel',
            'status', 'progress', 'undone', 'time_created', 'parent_step',
            'parent_step_pos', 'information_package',
        )
        read_only_fields = (
            'status', 'progress', 'time_created', 'time_done', 'undone',
        )


class ProcessStepDetailSerializer(ProcessStepSerializer):
    task_count = serializers.SerializerMethodField()
    failed_task_count = serializers.SerializerMethodField()
    exception = serializers.SerializerMethodField()
    traceback = serializers.SerializerMethodField()

    def get_task_count(self, obj):
        return obj.tasks.count()

    def get_failed_task_count(self, obj):
        return obj.tasks.filter(status=celery_states.FAILURE, undone__isnull=True).count()

    def get_exception(self, obj):
        t = obj.tasks.filter(status=celery_states.FAILURE, undone__isnull=True).first()
        if t:
            return t.exception

    def get_traceback(self, obj):
        t = obj.tasks.filter(status=celery_states.FAILURE, undone__isnull=True).first()
        if t:
            return t.traceback

    class Meta:
        model = ProcessStepSerializer.Meta.model
        fields = ProcessStepSerializer.Meta.fields + (
            'task_count', 'failed_task_count', 'exception', 'traceback'
        )
        read_only_fields = ProcessStepSerializer.Meta.read_only_fields + (
            'task_count', 'failed_task_count', 'exception', 'traceback'
        )
