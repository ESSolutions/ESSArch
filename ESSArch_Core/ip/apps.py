from django.apps import AppConfig


class IPConfig(AppConfig):
    name = 'ESSArch_Core.ip'
    verbose_name = 'Information Package'

    def ready(self):
        import ESSArch_Core.ip.signals  # noqa
