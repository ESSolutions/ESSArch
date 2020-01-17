import importlib

from django.conf import settings

AVAILABLE_TAPE_IDENTIFICATION_BACKENDS = {
    'base': 'ESSArch_Core.storage.tape_identification.backends.base.BaseTapeIdentificationBackend',
}

extra_backends = getattr(settings, 'ESSARCH_TAPE_IDENTIFICATION_BACKENDS', {})
AVAILABLE_TAPE_IDENTIFICATION_BACKENDS.update(extra_backends)


def get_backend(name):
    try:
        module_name, klass = AVAILABLE_TAPE_IDENTIFICATION_BACKENDS[name].rsplit('.', 1)
    except KeyError:
        raise ValueError('Tape identification backend "%s" not found' % name)

    return getattr(importlib.import_module(module_name), klass)()
