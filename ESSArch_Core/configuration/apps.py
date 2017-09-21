from django.apps import AppConfig


class ConfigurationConfig(AppConfig):
    name = 'ESSArch_Core.configuration'
    verbose_name = 'Configuration'

    def ready(self):
        import ESSArch_Core.configuration.signals  # noqa
