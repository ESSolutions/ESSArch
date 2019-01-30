import os

from _version import get_versions

from rest_framework import serializers

from ESSArch_Core.auth.fields import CurrentUsernameDefault
from ESSArch_Core.auth.serializers import UserSerializer
from ESSArch_Core.configuration.models import EventType
from ESSArch_Core.ip.models import Agent, AgentNote, EventIP, InformationPackage, Workarea

VERSION = get_versions()['version']


class AgentNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentNote
        fields = ('id', 'note')


class AgentSerializer(serializers.ModelSerializer):
    notes = AgentNoteSerializer(many=True, read_only=True)

    class Meta:
        model = Agent
        fields = ('id', 'role', 'type', 'name', 'code', 'notes')


class EventIPSerializer(serializers.HyperlinkedModelSerializer):
    linkingAgentIdentifierValue = serializers.CharField(read_only=True, default=CurrentUsernameDefault())
    information_package = serializers.CharField(required=False, source='linkingObjectIdentifierValue')
    eventType = serializers.PrimaryKeyRelatedField(queryset=EventType.objects.all())
    eventDetail = serializers.SlugRelatedField(slug_field='eventDetail', source='eventType', read_only=True)

    def create(self, validated_data):
        if 'linkingAgentIdentifierValue' not in validated_data:
            validated_data['linkingAgentIdentifierValue'] = self.context['request'].user
        return super(EventIPSerializer, self).create(validated_data)

    class Meta:
        model = EventIP
        fields = (
            'url', 'id', 'eventType', 'eventDateTime', 'eventDetail',
            'eventVersion', 'eventOutcome',
            'eventOutcomeDetailNote', 'linkingAgentIdentifierValue',
            'linkingAgentRole', 'information_package',
        )
        extra_kwargs = {
            'eventVersion': {
                'default': VERSION
            }
        }


class InformationPackageSerializer(serializers.ModelSerializer):
    responsible = UserSerializer(read_only=True)
    agents = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    package_type = serializers.ChoiceField(choices=InformationPackage.PACKAGE_TYPE_CHOICES)
    package_type_display = serializers.CharField(source='get_package_type_display')

    def get_agents(self, obj):
        agents = AgentSerializer(obj.agents.all(), many=True).data
        return {'{role}_{type}'.format(role=a['role'], type=a['type']): a for a in agents}

    def get_permissions(self, obj):
        user = getattr(self.context.get('request'), 'user', None)
        checker = self.context.get('perm_checker')
        return obj.get_permissions(user=user, checker=checker)

    class Meta:
        model = InformationPackage
        fields = (
            'url', 'id', 'label', 'object_identifier_value', 'object_size',
            'object_path', 'submission_agreement', 'submission_agreement_locked',
            'package_type', 'package_type_display', 'responsible', 'create_date',
            'object_num_items', 'entry_date', 'state', 'status', 'step_state',
            'archived', 'cached', 'aic', 'generation', 'agents',
            'policy', 'message_digest', 'message_digest_algorithm',
            'content_mets_create_date', 'content_mets_size', 'content_mets_digest_algorithm', 'content_mets_digest',
            'package_mets_create_date', 'package_mets_size', 'package_mets_digest_algorithm', 'package_mets_digest',
            'start_date', 'end_date', 'permissions', 'appraisal_date',
        )


class WorkareaSerializer(serializers.ModelSerializer):
    extracted = serializers.SerializerMethodField()
    packaged = serializers.SerializerMethodField()
    user = UserSerializer(read_only=True, default=serializers.CurrentUserDefault())
    type_name = serializers.SerializerMethodField()
    successfully_validated = serializers.JSONField(required=False, allow_null=True)

    def get_extracted(self, obj):
        return os.path.isdir(obj.path)

    def get_packaged(self, obj):
        return os.path.isfile(obj.path + '.tar')

    def get_type_name(self, obj):
        return obj.get_type_display()

    def create(self, validated_data):
        if 'user' not in validated_data:
            validated_data['user'] = self.context['request'].user
        return super(WorkareaSerializer, self).create(validated_data)

    class Meta:
        model = Workarea
        fields = (
            'id', 'user', 'ip', 'read_only', 'type', 'type_name',
            'extracted', 'packaged', 'successfully_validated',
        )
