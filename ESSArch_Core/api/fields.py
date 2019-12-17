import os

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class FilePathField(serializers.CharField):
    default_error_messages = {
        'invalid_path': _('{input} is not a valid path.'),
    }

    def __init__(self, path, **kwargs):
        self.path = path
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        if not os.path.exists(os.path.join(self.path, data)):
            self.fail('invalid_path', input=data)

        return data
