import importlib

from django.conf import settings

AVAILABLE_TRANSFORMERS = {}

extra_transformers = getattr(settings, 'ESSARCH_TRANSFORMERS', {})
AVAILABLE_TRANSFORMERS.update(extra_transformers)

PATH_VARIABLE = "_PATH"


def _transform_file(path, transformer, ip=None):
    pass


def _transform_directory(path, transformer, ip=None):
    pass


def transform_path(path, profile, data=None, ip=None, user=None):
    transformer = profile.specification.get('name')
    data = data or {}

    try:
        module_name, transformer_class_name = AVAILABLE_TRANSFORMERS[transformer].rsplit('.', 1)
    except KeyError:
        raise ValueError('Transformer "%s" not found' % transformer)

    transformer_class = getattr(importlib.import_module(module_name), transformer_class_name)

    specification = profile.specification
    options = specification.get('options', {})

    transformer_instance = transformer_class(ip=ip, options=options, data=data, user=user)
    transformer_instance.transform(path)
