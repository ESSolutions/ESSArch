import base64
import binascii

from django.conf import settings
from django.core.checks import Error, register


E001 = Error(
    'The ENCRYPTION_KEY setting must not be empty',
    id="essarch.E001"
)

E002 = Error(
    'ENCRYPTION_KEY must be 32 url-safe base64-encoded bytes',
    id="essarch.E002"
)


@register()
def encryption_key_check(app_configs, **kwargs):
    if not getattr(settings, 'ENCRYPTION_KEY', None):
        return [E001]

    key = settings.ENCRYPTION_KEY
    try:
        key = base64.urlsafe_b64decode(key)
    except binascii.Error:
        return [E002]

    if len(key) != 32:
        return [E002]

    return []
