from rest_framework import serializers

from ESSArch_Core.fixity.models import ActionTool, Validation, IPProfileOrder, ProfileDescription, ExternalToolDescription


class ActionToolSerializer(serializers.ModelSerializer):
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


class IPProfileOrderSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = IPProfileOrder
        fields = ('id', 'context', 'profile', 'information_package')

class ProfileDescriptionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfileDescription
        fields = ('id', 'description', 'profile')

class ExternalToolDescriptionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ExternalToolDescription
        fields = ('id', 'description', 'externalTool')