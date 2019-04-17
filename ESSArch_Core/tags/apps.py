from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class TagConfig(AppConfig):
    name = 'ESSArch_Core.tags'
    verbose_name = _('Archival Description')

    def ready(self):
        import ESSArch_Core.tags.signals  # noqa
