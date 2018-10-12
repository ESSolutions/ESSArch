from django.apps import AppConfig


class TagConfig(AppConfig):
    name = 'ESSArch_Core.tags'
    verbose_name = 'Tags'

    def ready(self):
        import ESSArch_Core.tags.signals  # noqa
