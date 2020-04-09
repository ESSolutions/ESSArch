import click
from rest_framework import serializers

from ESSArch_Core.api.fields import FilePathField


class BaseValidator:
    file_validator = True  # Does the validator operate on single files or entire directories?

    def __init__(self, context=None, include=None, exclude=None, options=None,
                 data=None, required=True, task=None, ip=None, responsible=None):
        """
        Initializes for validation of one or more files
        """
        self.context = context
        self.include = include or []
        self.exclude = exclude or []
        self.options = options or {}
        self.data = data or {}
        self.required = required
        self.task = task
        self.ip = ip
        self.responsible = responsible

    class Serializer(serializers.Serializer):
        context = serializers.CharField()

        def __init__(self, *args, **kwargs):
            from ESSArch_Core.ip.models import InformationPackage

            super().__init__(*args, **kwargs)
            ip_pk = kwargs['context']['information_package']
            ip = InformationPackage.objects.get(pk=ip_pk)
            self.fields['path'] = FilePathField(ip.object_path, allow_blank=True, default='')

    class OptionsSerializer(serializers.Serializer):
        pass

    @classmethod
    def get_serializer_class(cls):
        return cls.Serializer

    @classmethod
    def get_options_serializer_class(cls):
        return cls.OptionsSerializer

    def validate(self, filepath, expected=None):
        raise NotImplementedError('subclasses of BaseValidator must provide a validate() method')

    @staticmethod
    @click.command()
    def cli(path):
        raise NotImplementedError('Subclasses of BaseValidator must provide a cli() method')
