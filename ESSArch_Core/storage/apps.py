from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class StorageConfig(AppConfig):
    name = 'ESSArch_Core.storage'
    verbose_name = _('Storage')

    def ready(self):
        import ESSArch_Core.storage.signals  # noqa isort:skip
