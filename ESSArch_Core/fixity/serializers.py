from rest_framework import serializers

from ESSArch_Core.fixity.models import ActionTool, Validation, ActionToolProfileOrder, ActionToolProfileDescription, ActionToolDescription, ActionToolProfile


class ActionToolSerializer(serializers.ModelSerializer):
    form = serializers.JSONField(read_only=True)

    class Meta:
        model = ActionTool
        fields = ('name', 'form', 'description')

class SaveActionToolSerializer(serializers.ModelSerializer):
    form = serializers.JSONField(read_only=True)

    class Meta:
        model = ActionTool
        fields = ('name', 'form',)


class ValidationSerializer(serializers.ModelSerializer):
    specification = serializers.JSONField(read_only=True)

    class Meta:
        model = Validation
        fields = ('id', 'filename', 'validator', 'passed', 'message', 'specification',
                  'information_package', 'time_started', 'time_done', 'required', 'task')


class ValidationFilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Validation
        fields = ('id', 'filename', 'passed', 'time_started', 'time_done',)


class ActionToolProfileOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionToolProfileOrder
        fields = ('id', 'context', 'profile', 'information_package')

class ActionToolProfileDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionToolProfileDescription
        fields = ('id', 'description', 'profile')

class ActionToolDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionToolDescription
        fields = ('id', 'description', 'actionTool')

class ActionToolProfileSerializer(serializers.ModelSerializer):
    model = ActionToolProfile
    fields = ('id', 'profile', 'actionTool')