from rest_framework import serializers

from ESSArch_Core.fixity.models import ConversionTool, Validation
from ESSArch_Core.fixity.validation import AVAILABLE_VALIDATORS


class ConversionToolSerializer(serializers.ModelSerializer):
    form = serializers.JSONField(read_only=True)

    class Meta:
        model = ConversionTool
        fields = ('name', 'form',)


class ValidatorDataSerializer(serializers.Serializer):
    name = serializers.ChoiceField(choices=list(AVAILABLE_VALIDATORS.keys()))
    data = serializers.JSONField()


class ValidatorWorkflowSerializer(serializers.Serializer):
    validators = serializers.ListField(
        child=ValidatorDataSerializer()
    )


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
