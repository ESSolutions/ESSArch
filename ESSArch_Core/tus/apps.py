from django.apps import AppConfig


class TusConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ESSArch_Core.tus'

    def ready(self):
        # Import signals to register them
        import ESSArch_Core.tus.signals  # noqa
        print("Tus app ready: signals imported")
