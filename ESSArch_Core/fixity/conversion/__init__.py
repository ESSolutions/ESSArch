import importlib

from django.conf import settings

AVAILABLE_CONVERTERS = {}

extra_converters = getattr(settings, 'ESSARCH_CONVERTERS', {})
AVAILABLE_CONVERTERS.update(extra_converters)


def get_backend(name, *args, **kwargs):
    try:
        module_name, klass = AVAILABLE_CONVERTERS[name].rsplit('.', 1)
    except KeyError:
        raise ValueError('Converter backend "%s" not found' % name)

    return getattr(importlib.import_module(module_name), klass)(*args, **kwargs)
