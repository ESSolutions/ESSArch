import os

from celery import states as celery_states
from rest_framework import exceptions, serializers

from ESSArch_Core.api.serializers import UserFilteredPrimaryKeyRelatedField
from ESSArch_Core.auth.serializers import UserSerializer
from ESSArch_Core.exceptions import Locked
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.maintenance.models import (
    AppraisalJob,
    AppraisalTemplate,
    ConversionJob,
    ConversionTemplate,
    MaintenanceJob,
    MaintenanceTemplate,
)
from ESSArch_Core.tags.models import Tag


class MaintenanceTemplateSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True, default=serializers.CurrentUserDefault())
    public = serializers.BooleanField(default=True)

    def validate(self, data):
        user = self.context['request'].user

        if self.instance is not None:
            public = data.get('public', self.instance.public)
        else:
            public = data['public']

        if user.user_profile.current_organization is None and not public:
            raise serializers.ValidationError("You must be in an organization to create non-public templates")

        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user

        instance = super().create(validated_data)
        if not instance.public:
            org = validated_data['user'].user_profile.current_organization
            org.add_object(instance)

        return instance

    class Meta:
        model = MaintenanceTemplate
        fields = (
            'id', 'name', 'description', 'user', 'public',
        )


class MaintenanceJobSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True, default=serializers.CurrentUserDefault())
    label = serializers.CharField(required=False, allow_blank=True, default="")
    has_report = serializers.SerializerMethodField()

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if instance.status == celery_states.STARTED:
            raise Locked
        return super().update(instance, validated_data)

    def get_has_report(self, obj):
        return os.path.isfile(obj.get_report_pdf_path())

    class Meta:
        model = MaintenanceJob
        fields = (
            'id', 'label', 'purpose', 'template', 'status', 'start_date', 'end_date', 'user', 'has_report',
        )
        read_only_fields = ('end_date',)


class MaintenanceJobInformationPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InformationPackage
        fields = ('id', 'object_identifier_value', 'label', 'generation')


class MaintenanceJobInformationPackageWriteSerializer(serializers.ModelSerializer):
    information_packages = serializers.ListField(
        child=UserFilteredPrimaryKeyRelatedField(queryset=InformationPackage.objects.filter(archived=True))
    )

    class Meta:
        model = InformationPackage
        fields = ('information_packages',)


class AppraisalJobTagSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    archive = serializers.CharField()

    def get_name(self, obj):
        if obj.current_version is None:
            return str(obj.pk)

        return obj.current_version.name

    class Meta:
        model = Tag
        fields = ('id', 'name', 'archive')


class AppraisalJobTagWriteSerializer(serializers.ModelSerializer):
    tags = serializers.ListField(
        child=UserFilteredPrimaryKeyRelatedField(queryset=Tag.objects.all())
    )

    class Meta:
        model = Tag
        fields = ('tags',)


class AppraisalTemplateSerializer(MaintenanceTemplateSerializer):
    package_file_pattern = serializers.JSONField(allow_null=True, default=None)

    class Meta(MaintenanceTemplateSerializer.Meta):
        model = AppraisalTemplate
        fields = MaintenanceTemplateSerializer.Meta.fields + ('package_file_pattern',)


class AppraisalJobSerializer(MaintenanceJobSerializer):
    package_file_pattern = serializers.JSONField(allow_null=True, default=None)

    def validate_start_date(self, value):
        user = self.context['request'].user
        if not user.has_perm('maintenance.run_appraisaljob'):
            raise exceptions.PermissionDenied()

        return value

    class Meta(MaintenanceJobSerializer.Meta):
        model = AppraisalJob
        fields = MaintenanceJobSerializer.Meta.fields + ('package_file_pattern',)


class ConversionTemplateSerializer(MaintenanceTemplateSerializer):
    specification = serializers.JSONField()

    class Meta(MaintenanceTemplateSerializer.Meta):
        model = ConversionTemplate
        fields = MaintenanceTemplateSerializer.Meta.fields + ('specification',)


class ConversionJobSerializer(MaintenanceJobSerializer):
    specification = serializers.JSONField()

    def validate_start_date(self, value):
        user = self.context['request'].user
        if not user.has_perm('maintenance.run_conversionjob'):
            raise exceptions.PermissionDenied()

        return value

    def validate(self, data):
        start_date = data.get('start_date', getattr(self.instance, 'start_date', None))

        if start_date is not None:
            specification = data.get('specification', getattr(self.instance, 'specification', None))

            if specification is None or specification == {}:
                raise exceptions.ValidationError('Cannot schedule job without specification')

        return data

    class Meta(MaintenanceJobSerializer.Meta):
        model = ConversionJob
        fields = MaintenanceJobSerializer.Meta.fields + ('specification',)
