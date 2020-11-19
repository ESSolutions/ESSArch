import importlib

from django.conf import settings

AVAILABLE_IMPORTERS = {
    'eard_erms': 'ESSArch_Core.search.importers.earderms.EardErmsImporter',
    'single_records': 'ESSArch_Core.search.importers.single_records.SingleRecordsImporter',
}

extra_importers = getattr(settings, 'ESSARCH_IMPORTERS', {})
AVAILABLE_IMPORTERS.update(extra_importers)


def get_backend(name):
    try:
        module_name, validator_class = AVAILABLE_IMPORTERS[name].rsplit('.', 1)
    except KeyError:
        raise ValueError('Importer "%s" not found' % name)

    return getattr(importlib.import_module(module_name), validator_class)
