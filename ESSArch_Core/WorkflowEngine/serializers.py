from django.contrib.auth.models import User, Group

from rest_framework import serializers

from configuration.models import (
    Agent,
    EventType,
    Parameter,
    Path,
    Schema,
)

from ip.models import EventIP, InformationPackage

from preingest.models import ProcessStep, ProcessTask

from profiles.models import (
    SubmissionAgreement,
    ProfileTransferProject,
    ProfileContentType,
    ProfileDataSelection,
    ProfileClassification,
    ProfileImport,
    ProfileSubmitDescription,
    ProfileSIP,
    ProfileAIP,
    ProfileDIP,
    ProfileWorkflow,
    ProfilePreservationMetadata,
)

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
            'time_created', 'parent_step', 'information_package', 'child_steps',
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

class SubmissionAgreementSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = SubmissionAgreement
        #fields = (__all__,)

class ProfileTransferProjectSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfileTransferProject
        fields = '__all__'

class ProfileContentTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfileContentType
        fields = '__all__'

class ProfileDataSelectionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfileDataSelection
        fields = '__all__'

class ProfileClassificationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfileClassification
        fields = '__all__'

class ProfileImportSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfileImport
        fields = '__all__'

class ProfileSubmitDescriptionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfileSubmitDescription
        fields = '__all__'

class ProfileSIPSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfileSIP
        fields = '__all__'

class ProfileAIPSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfileAIP
        fields = '__all__'

class ProfileDIPSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfileDIP
        fields = '__all__'

class ProfileWorkflowSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfileWorkflow
        fields = '__all__'

class ProfilePreservationMetadataSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfilePreservationMetadata
        fields = '__all__'

class AgentSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Agent
        fields = '__all__'

class ParameterSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Parameter
        fields = '__all__'

class PathSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Path
        fields = '__all__'

class SchemaSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Schema
        fields = '__all__'
