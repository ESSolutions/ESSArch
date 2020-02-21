from celery import states as celery_states
from rest_framework import serializers

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


class MaintenanceTemplateSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True, default=serializers.CurrentUserDefault())
    public = serializers.BooleanField(default=True)
    package_file_pattern = serializers.JSONField(allow_null=True, default=None)

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
            'id', 'name', 'description', 'package_file_pattern', 'user', 'public',
        )


class MaintenanceJobSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True, default=serializers.CurrentUserDefault())
    label = serializers.CharField(required=False)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if instance.status == celery_states.STARTED:
            raise Locked
        return super().update(instance, validated_data)

    class Meta:
        model = MaintenanceJob
        fields = (
            'id', 'label', 'template', 'status', 'start_date', 'end_date', 'user',
        )
        read_only_fields = ('end_date',)


class AppraisalJobInformationPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InformationPackage
        fields = ('id',)


class AppraisalJobInformationPackageWriteSerializer(serializers.ModelSerializer):
    information_packages = serializers.ListField(
        child=UserFilteredPrimaryKeyRelatedField(queryset=InformationPackage.objects.filter(archived=True))
    )

    class Meta:
        model = InformationPackage
        fields = ('information_packages',)


class AppraisalTemplateSerializer(MaintenanceTemplateSerializer):
    class Meta(MaintenanceTemplateSerializer.Meta):
        model = AppraisalTemplate


class AppraisalJobSerializer(MaintenanceJobSerializer):
    class Meta(MaintenanceJobSerializer.Meta):
        model = AppraisalJob
        fields = MaintenanceJobSerializer.Meta.fields + ('package_file_pattern',)


class ConversionTemplateSerializer(MaintenanceTemplateSerializer):
    class Meta(MaintenanceTemplateSerializer.Meta):
        model = ConversionTemplate


class ConversionJobSerializer(MaintenanceJobSerializer):
    class Meta(MaintenanceJobSerializer.Meta):
        model = ConversionJob
        fields = MaintenanceJobSerializer.Meta.fields + ('specification',)
