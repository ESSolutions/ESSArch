import importlib

from django.conf import settings

AVAILABLE_RECEIPT_BACKENDS = {
    'email': 'ESSArch_Core.fixity.receipt.backends.email.EmailReceiptBackend',
    'xml': 'ESSArch_Core.fixity.receipt.backends.xml.XMLReceiptBackend',
}

extra_receipt_backends = getattr(settings, 'ESSARCH_RECEIPT_BACKENDS', {})
AVAILABLE_RECEIPT_BACKENDS.update(extra_receipt_backends)


def get_backend(name, *args, **kwargs):
    try:
        module_name, klass = AVAILABLE_RECEIPT_BACKENDS[name].rsplit('.', 1)
    except KeyError:
        raise ValueError('Receipt backend "%s" not found' % name)

    return getattr(importlib.import_module(module_name), klass)(*args, **kwargs)
