from rest_framework import serializers

from ESSArch_Core.auth.serializers import UserSerializer
from ESSArch_Core.maintenance.models import (
    AppraisalJob,
    AppraisalRule,
    ConversionJob,
    ConversionRule,
    MaintenanceJob,
    MaintenanceRule,
)


class MaintenanceRuleSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True, default=serializers.CurrentUserDefault())
    public = serializers.BooleanField(default=True)
    specification = serializers.JSONField(allow_null=True, default=None)

    def validate(self, data):
        user = self.context['request'].user
        if user.user_profile.current_organization is None and not data['public']:
            raise serializers.ValidationError("You must be in an organization to create non-public rules")

        return data

    def create(self, validated_data):
        if 'user' not in validated_data:
            validated_data['user'] = self.context['request'].user

        instance = super().create(validated_data)
        if not instance.public:
            org = validated_data['user'].user_profile.current_organization
            org.add_object(instance)

        return instance

    class Meta:
        model = MaintenanceRule
        fields = (
            'id', 'name', 'description', 'frequency', 'specification', 'user', 'public',
        )


class MaintenanceJobSerializer(serializers.ModelSerializer):
    rule = serializers.SerializerMethodField()
    user = UserSerializer(read_only=True, default=serializers.CurrentUserDefault())

    @staticmethod
    def create_rule_serializer(_model):
        class MaintenanceJobRuleSerializer(serializers.ModelSerializer):
            class Meta:
                model = _model
                fields = ('id', 'name',)

        return MaintenanceJobRuleSerializer

    def get_rule(self, obj):
        if obj.rule is None:
            return None

        return self.create_rule_serializer(obj.rule._meta.model)(instance=obj.rule).data

    def create(self, validated_data):
        if 'user' not in validated_data:
            validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    class Meta:
        model = MaintenanceJob
        fields = (
            'id', 'rule', 'status', 'start_date', 'end_date', 'user',
        )


class MaintenanceJobWriteSerializer(MaintenanceJobSerializer):
    pass


class AppraisalRuleSerializer(MaintenanceRuleSerializer):
    class Meta(MaintenanceRuleSerializer.Meta):
        model = AppraisalRule


class AppraisalJobSerializer(MaintenanceJobSerializer):
    class Meta(MaintenanceJobSerializer.Meta):
        model = AppraisalJob


class AppraisalJobWriteSerializer(MaintenanceJobWriteSerializer):
    rule = serializers.PrimaryKeyRelatedField(queryset=AppraisalRule.objects.all())

    class Meta(MaintenanceJobWriteSerializer.Meta):
        model = AppraisalJob


class ConversionRuleSerializer(MaintenanceRuleSerializer):
    class Meta(MaintenanceRuleSerializer.Meta):
        model = ConversionRule


class ConversionJobSerializer(MaintenanceJobSerializer):
    class Meta(MaintenanceJobSerializer.Meta):
        model = ConversionJob


class ConversionJobWriteSerializer(MaintenanceJobWriteSerializer):
    rule = serializers.PrimaryKeyRelatedField(queryset=ConversionRule.objects.all())

    class Meta(MaintenanceJobWriteSerializer.Meta):
        model = ConversionJob
