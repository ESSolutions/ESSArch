from rest_framework import serializers

from ESSArch_Core.fixity.models import ActionTool, Validation

from lxml import etree


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
    message = serializers.SerializerMethodField(read_only=True)

    def get_message(self, obj):
        if 'stylesheet' in obj.specification.keys():
            parser = etree.XMLParser(remove_blank_text=True)
            root = etree.XML(obj.message, parser=parser)            
            xslt = etree.parse(obj.specification.get('stylesheet'))
            transform = etree.XSLT(xslt)
            message = str(transform(root))
            return message
        else:
            return obj.message

    class Meta:
        model = Validation
        fields = ('id', 'filename', 'validator', 'passed', 'message', 'specification',
                  'information_package', 'time_started', 'time_done', 'required', 'task')


class ValidationFilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Validation
        fields = ('id', 'filename', 'passed', 'time_started', 'time_done',)
