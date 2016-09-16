from django.contrib.auth.models import User, Group

from rest_framework import serializers

from configuration.models import (
    Agent,
    EventType,
    Parameter,
    Path,
    Schema,
)

from ip.models import (
    ArchivalInstitution,
    ArchivistOrganization,
    ArchivalType,
    ArchivalLocation,
    EventIP,
    InformationPackage
)

from preingest.models import ProcessStep, ProcessTask
from preingest.util import available_tasks

from profiles.models import (
    SubmissionAgreement,
    Profile,
    ProfileLock,
    ProfileRel,
)

class PickledObjectField(serializers.Field):
    def to_representation(self, obj):
        return obj

    def to_internal_value(self, data):
        return data


class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class ArchivalInstitutionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ArchivalInstitution
        fields = ('url', 'id', 'name', 'information_packages',)

class ArchivistOrganizationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ArchivistOrganization
        fields = ('url', 'id', 'name', 'information_packages',)

class ArchivalTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ArchivalType
        fields = ('url', 'id', 'name', 'information_packages',)

class ArchivalLocationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ArchivalLocation
        fields = ('url', 'id', 'name', 'information_packages',)


class ProcessTaskSerializer(serializers.HyperlinkedModelSerializer):
    available = available_tasks()

    TASK_CHOICES = zip(
        ["preingest.tasks."+t for t in available],
        available
    )

    name =  serializers.ChoiceField(
        choices=TASK_CHOICES,
    )

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

class ProcessStepSerializer(serializers.HyperlinkedModelSerializer):
    tasks = ProcessTaskSerializer(many=True, read_only=True)
    child_steps = RecursiveField(many=True, read_only=True)

    class Meta:
        model = ProcessStep
        fields = (
            'url', 'id', 'name', 'result', 'type', 'user', 'parallel',
            'status', 'progress', 'time_created', 'parent_step',
            'parent_step_pos', 'information_package', 'child_steps', 'tasks',
            'task_set',
        )


class ProfileLockSerializer(serializers.ModelSerializer):
    submission_agreement = serializers.HyperlinkedIdentityField(
        view_name='submissionagreement-detail',
        lookup_field="submission_agreement_id",
        lookup_url_kwarg="pk"
    )

    profile = serializers.HyperlinkedIdentityField(
        view_name='profile-detail',
        lookup_field="profile_id",
        lookup_url_kwarg="pk"
    )

    class Meta:
        model = ProfileLock
        fields = (
            'id', 'submission_agreement', 'profile',
        )


class InformationPackageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = InformationPackage
        fields = (
            'url', 'id', 'Label', 'Content', 'Responsible', 'CreateDate',
            'State', 'status', 'ObjectSize', 'ObjectNumItems', 'ObjectPath',
            'Startdate', 'Enddate', 'OAIStype', 'SubmissionAgreement',
            'ArchivalInstitution', 'ArchivistOrganization', 'ArchivalType',
            'ArchivalLocation', 'steps', 'events',
        )


class InformationPackageDetailSerializer(InformationPackageSerializer):
    locks = ProfileLockSerializer(many=True, read_only=True)
    steps = ProcessStepSerializer(many=True, read_only=True)

    class Meta:
        model = InformationPackageSerializer.Meta.model
        fields = InformationPackageSerializer.Meta.fields + ('locks',)


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


class ProfileRelSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField(source='profile.id')
    name = serializers.ReadOnlyField(source='profile.name')
    url = serializers.HyperlinkedIdentityField(
        view_name='profile-detail',
        lookup_field="profile_id",
        lookup_url_kwarg="pk"
    )

    class Meta:
        model = ProfileRel
        fields = ('url', 'id', 'name', 'status',)


class SubmissionAgreementSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    profile_transfer_project = ProfileRelSerializer(
        source="profile_transfer_project_rel",
        many=True,
        read_only=True,
    )
    profile_content_type = ProfileRelSerializer(
        source="profile_content_type_rel",
        many=True,
        read_only=True,
    )
    profile_data_selection = ProfileRelSerializer(
        source="profile_data_selection_rel",
        many=True,
        read_only=True,
    )
    profile_classification = ProfileRelSerializer(
        source="profile_classification_rel",
        many=True,
        read_only=True,
    )
    profile_import = ProfileRelSerializer(
        source="profile_import_rel",
        many=True,
        read_only=True,
    )
    profile_submit_description = ProfileRelSerializer(
        source="profile_submit_description_rel",
        many=True,
        read_only=True,
    )
    profile_sip = ProfileRelSerializer(
        source="profile_sip_rel",
        many=True,
        read_only=True,
    )
    profile_aip = ProfileRelSerializer(
        source="profile_aip_rel",
        many=True,
        read_only=True,
    )
    profile_dip = ProfileRelSerializer(
        source="profile_dip_rel",
        many=True,
        read_only=True,
    )
    profile_workflow = ProfileRelSerializer(
        source="profile_workflow_rel",
        many=True,
        read_only=True,
    )
    profile_preservation_metadata = ProfileRelSerializer(
        source="profile_preservation_metadata_rel",
        many=True,
        read_only=True,
    )
    profile_event = ProfileRelSerializer(
        source="profile_event_rel",
        many=True,
        read_only=True,
    )

    class Meta:
        model = SubmissionAgreement
        fields = (
                'url', 'id', 'sa_name', 'sa_type', 'sa_status', 'sa_label',
                'sa_cm_version', 'sa_cm_release_date',
                'sa_cm_change_authority', 'sa_cm_change_description',
                'sa_cm_sections_affected', 'sa_producer_organization',
                'sa_producer_main_name', 'sa_producer_main_address',
                'sa_producer_main_phone', 'sa_producer_main_email',
                'sa_producer_main_additional', 'sa_producer_individual_name',
                'sa_producer_individual_role', 'sa_producer_individual_phone',
                'sa_producer_individual_email',
                'sa_producer_individual_additional',
                'sa_archivist_organization', 'sa_archivist_main_name',
                'sa_archivist_main_address', 'sa_archivist_main_phone',
                'sa_archivist_main_email', 'sa_archivist_main_additional',
                'sa_archivist_individual_name', 'sa_archivist_individual_role',
                'sa_archivist_individual_phone',
                'sa_archivist_individual_email',
                'sa_archivist_individual_additional',
                'sa_designated_community_description',
                'sa_designated_community_individual_name',
                'sa_designated_community_individual_role',
                'sa_designated_community_individual_phone',
                'sa_designated_community_individual_email',
                'sa_designated_community_individual_additional',
                'profile_transfer_project', 'profile_content_type',
                'profile_data_selection', 'profile_classification',
                'profile_import', 'profile_submit_description', 'profile_sip',
                'profile_aip', 'profile_dip', 'profile_workflow',
                'profile_preservation_metadata', 'profile_event',
                'information_packages',
        )
class ProfileSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Profile
        fields = (
            'url', 'id', 'profile_type', 'name', 'type', 'status', 'label',
            'representation_info', 'preservation_descriptive_info',
            'supplemental', 'access_constraints', 'datamodel_reference',
            'additional', 'submission_method', 'submission_schedule',
            'submission_data_inventory', 'structure', 'template',
            'specification', 'specification_data', 'submission_agreements',
        )

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
