from django.db import models
from jsonfield.encoder import JSONEncoder
from jsonfield.fields import DEFAULT_LOAD_KWARGS, JSONField as JSONField2

DEFAULT_DUMP_KWARGS = {
    'cls': JSONEncoder,
    'indent': 2,
    'separators': (',', ':'),
}


class JSONField(JSONField2):
    def __init__(self, *args, dump_kwargs=None, **kwargs):
        super().__init__(*args, dump_kwargs=DEFAULT_DUMP_KWARGS, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = models.Field.deconstruct(self)

        if self.dump_kwargs != DEFAULT_DUMP_KWARGS:
            kwargs['dump_kwargs'] = self.dump_kwargs
        if self.load_kwargs != DEFAULT_LOAD_KWARGS:
            kwargs['load_kwargs'] = self.load_kwargs
        return name, path, args, kwargs
