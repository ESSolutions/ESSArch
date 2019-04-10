import importlib

from django.conf import settings

import sys
import logging
logger = logging.getLogger('essarch.auth.saml.mapping')
logger.info(sys.path)


def get_backend():
    backend = getattr(settings, 'ESSARCH_SAML_MAPPING_BACKEND', None)

    if backend is None:
        return None

    module_name, cls = backend.rsplit('.', 1)
    return getattr(importlib.import_module(module_name), cls)
