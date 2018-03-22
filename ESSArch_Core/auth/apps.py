from django.apps import AppConfig

class AuthConfig(AppConfig):
    name = 'ESSArch_Core.auth'
    label = 'essauth'

    def ready(self):
        import ESSArch_Core.auth.signals  # noqa
