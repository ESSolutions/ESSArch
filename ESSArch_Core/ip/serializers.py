import errno
import os

from ESSArch_Core.api.serializers import DynamicHyperlinkedModelSerializer
from ESSArch_Core.configuration.serializers import ArchivePolicySerializer
from ESSArch_Core.profiles.models import SubmissionAgreement
from _version import get_versions

from rest_framework import serializers, filters

from ESSArch_Core.auth.fields import CurrentUsernameDefault
from ESSArch_Core.auth.serializers import UserSerializer
from ESSArch_Core.configuration.models import EventType
from ESSArch_Core.ip.models import Agent, AgentNote, EventIP, InformationPackage, Order, Workarea
from ESSArch_Core.profiles.serializers import ProfileIPSerializer
from ESSArch_Core.profiles.utils import profile_types

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
        return super().create(validated_data)

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
    profiles = serializers.SerializerMethodField()

    workarea = serializers.SerializerMethodField()
    aic = serializers.PrimaryKeyRelatedField(queryset=InformationPackage.objects.all())
    first_generation = serializers.SerializerMethodField()
    last_generation = serializers.SerializerMethodField()

    def get_profiles(self, obj):
        profiles = getattr(obj, 'profiles', obj.profileip_set)
        return ProfileIPSerializer(profiles, many=True, context=self.context).data

    def get_agents(self, obj):
        try:
            agent_objs = obj.prefetched_agents
        except AttributeError:
            agent_objs = obj.agents.all()
        agents = AgentSerializer(agent_objs, many=True).data
        return {'{role}_{type}'.format(role=a['role'], type=a['type']): a for a in agents}

    def get_permissions(self, obj):
        user = getattr(self.context.get('request'), 'user', None)
        checker = self.context.get('perm_checker')
        return obj.get_permissions(user=user, checker=checker)

    def to_representation(self, obj):
        data = super().to_representation(obj)
        profiles = data['profiles']
        data['profiles'] = {}

        for ptype in profile_types:
            data['profile_%s' % ptype] = None

        for p in profiles:
            data['profile_%s' % p['profile_type']] = p

        data.pop('profiles', None)

        return data

    def get_first_generation(self, obj):
        if hasattr(obj, 'first_generation'):
            return obj.first_generation

        return obj.is_first_generation()

    def get_last_generation(self, obj):
        if hasattr(obj, 'last_generation'):
            return obj.last_generation

        return obj.is_last_generation()

    def get_workarea(self, obj):
        try:
            workareas = obj.prefetched_workareas
        except AttributeError:
            request = self.context.get('request')
            see_all = request.user.has_perm('ip.see_all_in_workspaces')
            workareas = obj.workareas.all()

            if not see_all:
                workareas = workareas.filter(user=request.user)

        return WorkareaSerializer(workareas, many=True, context=self.context).data

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
            'start_date', 'end_date', 'permissions', 'appraisal_date', 'profiles',
            'workarea', 'first_generation', 'last_generation',
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'validators': [],
            },
            'object_identifier_value': {
                'read_only': False,
                'validators': [],
            },
        }


class OrderSerializer(serializers.HyperlinkedModelSerializer):
    responsible = UserSerializer(read_only=True, default=serializers.CurrentUserDefault())

    information_packages = serializers.HyperlinkedRelatedField(
        many=True, required=False, view_name='informationpackage-detail',
        queryset=InformationPackage.objects.filter(
            package_type=InformationPackage.DIP
        )
    )

    def save(self, **kwargs):
        kwargs["responsible"] = self.fields["responsible"].get_default()
        return super().save(**kwargs)

    class Meta:
        model = Order
        fields = (
            'url', 'id', 'label', 'responsible', 'information_packages',
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
        return super().create(validated_data)

    class Meta:
        model = Workarea
        fields = (
            'id', 'user', 'ip', 'read_only', 'type', 'type_name',
            'extracted', 'packaged', 'successfully_validated',
        )


class InformationPackageAICSerializer(DynamicHyperlinkedModelSerializer):
    information_packages = InformationPackageSerializer(read_only=True, many=True)
    package_type = serializers.ChoiceField(choices=((1, 'AIC'),))

    class Meta:
        model = InformationPackageSerializer.Meta.model
        fields = (
            'id', 'label', 'object_identifier_value',
            'package_type', 'responsible', 'create_date',
            'entry_date', 'information_packages', 'appraisal_date',
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'validators': [],
            },
            'object_identifier_value': {
                'read_only': False,
                'validators': [],
            },
        }


class InformationPackageDetailSerializer(InformationPackageSerializer):
    aic = InformationPackageAICSerializer(omit=['information_packages'])
    policy = ArchivePolicySerializer()
    submission_agreement = serializers.PrimaryKeyRelatedField(queryset=SubmissionAgreement.objects.all())
    archive = serializers.SerializerMethodField()
    has_cts = serializers.SerializerMethodField()

    def get_archive(self, obj):
        try:
            return str(obj.get_archive_tag().tag.current_version.pk)
        except AttributeError:
            return None

    def get_has_cts(self, obj):
        try:
            return obj.get_profile('content_type') is not None and obj.get_content_type_file() is not None
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
            return False

    class Meta:
        model = InformationPackageSerializer.Meta.model
        fields = InformationPackageSerializer.Meta.fields + (
            'submission_agreement', 'submission_agreement_locked', 'archive', 'has_cts',
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'validators': [],
            },
            'object_identifier_value': {
                'read_only': False,
                'validators': [],
            },
        }


class NestedInformationPackageSerializer(DynamicHyperlinkedModelSerializer):
    responsible = UserSerializer(read_only=True)
    package_type = serializers.ChoiceField(choices=InformationPackage.PACKAGE_TYPE_CHOICES)
    package_type_display = serializers.SerializerMethodField()
    information_packages = serializers.SerializerMethodField()
    aic = serializers.PrimaryKeyRelatedField(queryset=InformationPackage.objects.all())
    submission_agreement = serializers.PrimaryKeyRelatedField(queryset=SubmissionAgreement.objects.all())
    workarea = serializers.SerializerMethodField()
    first_generation = serializers.SerializerMethodField()
    last_generation = serializers.SerializerMethodField()
    new_version_in_progress = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    agents = serializers.SerializerMethodField()

    search_filter = filters.SearchFilter()

    def get_package_type_display(self, obj):
        return obj.get_package_type_display()

    def get_permissions(self, obj):
        user = getattr(self.context.get('request'), 'user', None)
        checker = self.context.get('perm_checker')
        return obj.get_permissions(user=user, checker=checker)

    def get_agents(self, obj):
        try:
            agent_objs = obj.prefetched_agents
        except AttributeError:
            agent_objs = obj.agents.all()
        agents = AgentSerializer(agent_objs, many=True).data
        return {'{role}_{type}'.format(role=a['role'], type=a['type']): a for a in agents}

    def get_information_packages(self, obj):
        request = self.context['request']
        return InformationPackageSerializer(
            obj.related_ips(),
            many=True,
            context={'request': request, 'perm_checker': self.context.get('perm_checker')}
        ).data

    def get_workarea(self, obj):
        try:
            workareas = obj.prefetched_workareas
        except AttributeError:
            request = self.context.get('request')
            see_all = request.user.has_perm('ip.see_all_in_workspaces')
            workareas = obj.workareas.all()

            if not see_all:
                workareas = workareas.filter(user=request.user)

        return WorkareaSerializer(workareas, many=True, context=self.context).data

    def get_first_generation(self, obj):
        if hasattr(obj, 'first_generation'):
            return obj.first_generation

        return obj.is_first_generation()

    def get_last_generation(self, obj):
        if hasattr(obj, 'last_generation'):
            return obj.last_generation

        return obj.is_last_generation()

    def get_new_version_in_progress(self, obj):
        new = obj.new_version_in_progress()
        if new is None:
            return None
        return WorkareaSerializer(new, context=self.context).data

    class Meta:
        model = InformationPackage
        fields = (
            'url', 'id', 'label', 'object_identifier_value', 'package_type', 'package_type_display',
            'responsible', 'create_date', 'entry_date', 'state', 'status',
            'step_state', 'archived', 'cached', 'aic', 'information_packages',
            'generation', 'policy', 'message_digest', 'agents',
            'message_digest_algorithm', 'submission_agreement',
            'submission_agreement_locked', 'workarea', 'object_size',
            'first_generation', 'last_generation', 'start_date', 'end_date',
            'new_version_in_progress', 'appraisal_date', 'permissions',
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'validators': [],
            },
            'object_identifier_value': {
                'read_only': False,
                'validators': [],
            },
        }

