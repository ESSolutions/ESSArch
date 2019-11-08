from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AuthConfig(AppConfig):
    name = 'ESSArch_Core.auth'
    verbose_name = _('Authentication and Authorization')
    label = 'essauth'

    def ready(self):
        import ESSArch_Core.auth.signals  # noqa isort:skip
