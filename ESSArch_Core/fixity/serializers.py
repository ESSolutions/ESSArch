from rest_framework import serializers

from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation import AVAILABLE_VALIDATORS
from ESSArch_Core.ip.models import InformationPackage


class ValidatorDataSerializer(serializers.Serializer):
    name = serializers.ChoiceField(choices=list(AVAILABLE_VALIDATORS.keys()))
    path = serializers.CharField(label='Path to validate', allow_blank=True, default='')
    context = serializers.CharField(label='Metadata file', allow_blank=True, default='')
    options = serializers.JSONField(required=False)


class ValidatorWorkflowSerializer(serializers.Serializer):
    information_package = serializers.PrimaryKeyRelatedField(queryset=InformationPackage.objects.all())
    validators = serializers.ListField(
        child=ValidatorDataSerializer(),
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
