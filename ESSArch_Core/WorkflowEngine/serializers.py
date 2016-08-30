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
    Profile,
    ProfileTransferProjectRel,
    ProfileContentTypeRel,
    ProfileDataSelectionRel,
    ProfileClassificationRel,
    ProfileImportRel,
    ProfileSubmitDescriptionRel,
    ProfileSIPRel,
    ProfileAIPRel,
    ProfileDIPRel,
    ProfileWorkflowRel,
    ProfilePreservationMetadataRel,
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
            'url', 'id', 'name', 'result', 'type', 'user', 'parallel',
            'status', 'progress', 'time_created', 'parent_step',
            'parent_step_pos', 'information_package', 'child_steps', 'tasks',
            'task_set',
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
        fields = ('url', 'id', 'username', 'email', 'groups')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'id', 'name')

class ProfileTransferProjectRelSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField(source='profiletransferproject.id')

    class Meta:
        model = ProfileTransferProjectRel
        fields = ('id', 'status',)

class ProfileContentTypeRelSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField(source='profilecontenttype.id')

    class Meta:
        model = ProfileContentTypeRel
        fields = ('id', 'status',)

class ProfileDataSelectionRelSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField(source='profiledataselection.id')

    class Meta:
        model = ProfileDataSelectionRel
        fields = ('id', 'status',)

class ProfileClassificationRelSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField(source='profileclassification.id')

    class Meta:
        model = ProfileClassificationRel
        fields = ('id', 'status',)

class ProfileImportRelSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField(source='profileimport.id')

    class Meta:
        model = ProfileImportRel
        fields = ('id', 'status',)

class ProfileSubmitDescriptionRelSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField(source='profilesubmitdescription.id')

    class Meta:
        model = ProfileSubmitDescriptionRel
        fields = ('id', 'status',)

class ProfileSIPRelSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField(source='profilesip.id')

    class Meta:
        model = ProfileSIPRel
        fields = ('id', 'status',)

class ProfileAIPRelSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField(source='profileaip.id')

    class Meta:
        model = ProfileAIPRel
        fields = ('id', 'status',)

class ProfileDIPRelSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField(source='profiledip.id')

    class Meta:
        model = ProfileDIPRel
        fields = ('id', 'status',)

class ProfileWorkflowRelSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField(source='profileworkflow.id')

    class Meta:
        model = ProfileWorkflowRel
        fields = ('id', 'status',)

class ProfilePreservationMetadataRelSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField(source='profilepreservationmetadata.id')

    class Meta:
        model = ProfilePreservationMetadataRel
        fields = ('id', 'status',)

class SubmissionAgreementSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    profile_transfer_project = ProfileTransferProjectRelSerializer(
        source='profiletransferprojectrel_set',
        many=True
    )
    profile_content_type = ProfileContentTypeRelSerializer(
        source='profilecontenttyperel_set',
        many=True
    )
    profile_data_selection = ProfileDataSelectionRelSerializer(
        source='profiledataselectionrel_set',
        many=True
    )
    profile_classification = ProfileClassificationRelSerializer(
        source='profileclassificationrel_set',
        many=True
    )
    profile_import = ProfileImportRelSerializer(
        source='profileimportrel_set',
        many=True
    )
    profile_submit_description= ProfileSubmitDescriptionRelSerializer(
        source='profilesubmitdescriptionrel_set',
        many=True
    )
    profile_sip = ProfileSIPRelSerializer(
        source='profilesiprel_set',
        many=True
    )
    profile_aip = ProfileAIPRelSerializer(
        source='profileaiprel_set',
        many=True
    )
    profile_dip = ProfileDIPRelSerializer(
        source='profilediprel_set',
        many=True
    )
    profile_workflow = ProfileWorkflowRelSerializer(
        source='profileworkflowrel_set',
        many=True
    )
    profile_preservation_metadata = ProfilePreservationMetadataRelSerializer(
        source='profilepreservationmetadatarel_set',
        many=True
    )

    class Meta:
        model = SubmissionAgreement
        fields = '__all__'

class ProfileSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Profile
        fields = '__all__'

class AgentSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Agent
        fields = '__all__'

class ParameterSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Parameter
        fields = '__all__'

class PathSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Path
        fields = '__all__'

class SchemaSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Schema
        fields = '__all__'
