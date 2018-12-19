from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class IPConfig(AppConfig):
    name = 'ESSArch_Core.ip'
    verbose_name = _('Information Package')

    def ready(self):
        import ESSArch_Core.ip.signals  # noqa
