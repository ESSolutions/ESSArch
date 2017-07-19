from _version import get_versions

from logging import Handler


class DBHandler(Handler):
    model_name = 'ESSArch_Core.ip.models.EventIP'

    def __init__(self, application="ESSArch"):
        Handler.__init__(self)
        self.application = application
        self.version = get_versions()['version']

    def emit(self, record):
        try:
            EventIP = self.get_model(self.model_name)
        except:
            from ESSArch_Core.ip.models import EventIP

        EventIP.objects.create(
            eventType_id=record.type,
            application=self.application,
            task_id=record.task,
            eventVersion=self.version,
            eventOutcome=record.levelno,
            eventOutcomeDetailNote=record.getMessage(),
            linkingAgentIdentifierValue_id=record.user,
            linkingObjectIdentifierValue_id=record.ip
        )

    def get_model(self, name):
        names = name.split('.')
        mod = __import__('.'.join(names[:-1]), fromlist=names[-1:])
        return getattr(mod, names[-1])
