from rest_framework import serializers

from ESSArch_Core.fixity.models import ConversionTool, Validation


class ConversionToolSerializer(serializers.ModelSerializer):
    form = serializers.JSONField(read_only=True)

    class Meta:
        model = ConversionTool
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
