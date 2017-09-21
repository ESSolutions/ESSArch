from _version import get_versions

from logging import Handler


class DBHandler(Handler):
    model_name = 'ESSArch_Core.ip.models.EventIP'
    event_type_model_name = 'ESSArch_Core.configuration.models.EventType'

    def __init__(self, application="ESSArch"):
        Handler.__init__(self)
        self.application = application
        self.version = get_versions()['version']

    def emit(self, record):
        try:
            EventIP = self.get_model(self.model_name)
        except:
            from ESSArch_Core.ip.models import EventIP

        try:
            EventType = self.get_model(self.event_type_model_name)
        except:
            from ESSArch_Core.configuration.models import EventType

        if getattr(record, 'event_type', None) is None:
            return

        forced = getattr(record, 'force', False)
        enabled = False

        if not forced:
            enabled = EventType.objects.values_list('enabled', flat=True).get(pk=record.event_type)

        if enabled or forced:
            EventIP.objects.create(
                eventType_id=record.event_type,
                application=self.application,
                task_id=getattr(record, 'task', None),
                eventVersion=self.version,
                eventOutcome=getattr(record, 'outcome', EventIP.SUCCESS if record.levelno < 40 else EventIP.FAILURE),
                eventOutcomeDetailNote=record.getMessage(),
                linkingAgentIdentifierValue=getattr(record, 'agent', ''),
                linkingObjectIdentifierValue=getattr(record, 'object', '')
            )

    def get_model(self, name):
        names = name.split('.')
        mod = __import__('.'.join(names[:-1]), fromlist=names[-1:])
        return getattr(mod, names[-1])
