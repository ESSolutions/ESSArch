from django.apps import AppConfig


class WorkflowEngineConfig(AppConfig):
    name = 'ESSArch_Core.WorkflowEngine'
    verbose_name = 'Workflow Engine'

    def ready(self):
        import ESSArch_Core.WorkflowEngine.signals  # noqa
