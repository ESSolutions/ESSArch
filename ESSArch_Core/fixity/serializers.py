from rest_framework import serializers

from ESSArch_Core.fixity.models import Validation


class ValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Validation
        fields = ('id', 'filename', 'validator', 'passed', 'message',
                  'information_package', 'time_started', 'time_done', 'required', 'task')


class ValidationFilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Validation
        fields = ('id', 'filename', 'passed', 'time_started', 'time_done',)
