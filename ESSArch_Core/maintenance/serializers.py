from rest_framework import serializers

from ESSArch_Core.auth.serializers import UserSerializer
from ESSArch_Core.maintenance.models import (AppraisalJob, AppraisalRule,
                                             ConversionJob, ConversionRule,
                                             MaintenanceJob, MaintenanceRule)


class MaintenanceRuleSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True, default=serializers.CurrentUserDefault())

    def validate(self, data):
        if data['user'].user_profile.current_organization is None and not data['public']:
            raise serializers.ValidationError("You must be in an organization to create non-public rules")

        return data

    def create(self, data):
        instance = super(MaintenanceRuleSerializer, self).create(validated_data=data)
        if not instance.public:
            org = data['user'].user_profile.current_organization
            org.add_object(instance)

        return instance

    class Meta:
        model = MaintenanceRule
        fields = (
            'id', 'name', 'frequency', 'specification', 'user', 'public',
        )


class MaintenanceJobSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True, default=serializers.CurrentUserDefault())

    class Meta:
        model = MaintenanceJob
        fields = (
            'id', 'rule', 'status', 'start_date', 'end_date', 'user',
        )


class AppraisalRuleSerializer(MaintenanceRuleSerializer):
    class Meta(MaintenanceRuleSerializer.Meta):
        model = AppraisalRule


class AppraisalJobSerializer(MaintenanceJobSerializer):
    class Meta(MaintenanceJobSerializer.Meta):
        model = AppraisalJob


class ConversionRuleSerializer(MaintenanceRuleSerializer):
    def validate_specification(self, value):
        """
        Ensure that the specification is not empty
        """

        if not value:
            raise serializers.ValidationError("Specification cannot be empty")
        return value
    class Meta(MaintenanceRuleSerializer.Meta):
        model = ConversionRule


class ConversionJobSerializer(MaintenanceJobSerializer):
    class Meta(MaintenanceJobSerializer.Meta):
        model = ConversionJob
