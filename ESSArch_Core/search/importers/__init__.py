import importlib

from django.conf import settings

AVAILABLE_CONTENT_TYPE_IMPORTERS = {
    'eard_erms': 'ESSArch_Core.search.importers.earderms.EardErmsImporter',
}

extra_content_type_importers = getattr(settings, 'ESSARCH_CONTENT_TYPE_IMPORTERS', {})
AVAILABLE_CONTENT_TYPE_IMPORTERS.update(extra_content_type_importers)


def get_content_type_importer(name):
    try:
        module_name, validator_class = AVAILABLE_CONTENT_TYPE_IMPORTERS[name].rsplit('.', 1)
    except KeyError:
        raise ValueError('Content type importer "%s" not found' % name)

    return getattr(importlib.import_module(module_name), validator_class)
