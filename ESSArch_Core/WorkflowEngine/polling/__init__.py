import importlib

from django.conf import settings

AVAILABLE_POLLERS = {}
extra_pollers = getattr(settings, 'ESSARCH_WORKFLOW_POLLERS', {})
AVAILABLE_POLLERS.update(extra_pollers)


def get_backend(name):
    try:
        module_name, class_name = AVAILABLE_POLLERS[name]['class'].rsplit('.', 1)
    except KeyError:
        raise ValueError('Poller "%s" not found' % name)

    return getattr(importlib.import_module(module_name), class_name)()
