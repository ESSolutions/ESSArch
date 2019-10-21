from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ConfigConfig(AppConfig):
    name = 'ESSArch_Core.config'
    verbose_name = _('Config')

    def ready(self):
        import ESSArch_Core.config.checks  # noqa isort:skip
