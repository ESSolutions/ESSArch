import importlib
import logging

from django.conf import settings

logger = logging.getLogger('essarch.storage')

AVAILABLE_STORAGE_BACKENDS = {
    'disk': 'ESSArch_Core.storage.backends.disk.DiskStorageBackend',
    'tape': 'ESSArch_Core.storage.backends.tape.TapeStorageBackend',
}

extra_storage_backends = getattr(settings, 'ESSARCH_STORAGE_BACKENDS', {})
AVAILABLE_STORAGE_BACKENDS.update(extra_storage_backends)


def get_backend(name):
    try:
        module_name, validator_class = AVAILABLE_STORAGE_BACKENDS[name].rsplit('.', 1)
    except KeyError:
        raise ValueError('Storage backend "%s" not found' % name)

    return getattr(importlib.import_module(module_name), validator_class)
