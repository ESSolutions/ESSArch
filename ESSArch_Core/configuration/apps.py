from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ConfigurationConfig(AppConfig):
    name = 'ESSArch_Core.configuration'
    verbose_name = _('Configuration')

    def ready(self):
        import ESSArch_Core.configuration.signals  # noqa isort:skip
