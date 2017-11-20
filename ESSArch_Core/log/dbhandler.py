from _version import get_versions

from logging import Handler

from django.core.cache import cache

class DBHandler(Handler):
    model_name = 'ESSArch_Core.ip.models.EventIP'
    event_type_model_name = 'ESSArch_Core.configuration.models.EventType'

    def __init__(self, application="ESSArch", agent_role=""):
        Handler.__init__(self)
        self.application = application
        self.agent_role = agent_role
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
            cache_name = 'event_type_%s_enabled' % record.event_type
            enabled = cache.get(cache_name)

            if enabled is None:
                enabled = EventType.objects.values_list('enabled', flat=True).get(pk=record.event_type)
                cache.set(cache_name, enabled, 3600)

        if enabled or forced:
            obj = getattr(record, 'object', '')
            if obj is None:
                obj = ''

            agent = getattr(record, 'agent', '')
            if agent is None:
                agent = ''

            EventIP.objects.create(
                eventType_id=record.event_type,
                application=self.application,
                task_id=getattr(record, 'task', None),
                eventVersion=self.version,
                eventOutcome=getattr(record, 'outcome', EventIP.SUCCESS if record.levelno < 40 else EventIP.FAILURE),
                eventOutcomeDetailNote=record.getMessage(),
                linkingAgentIdentifierValue=agent,
                linkingAgentRole=self.agent_role,
                linkingObjectIdentifierValue=obj,
            )

    def get_model(self, name):
        names = name.split('.')
        mod = __import__('.'.join(names[:-1]), fromlist=names[-1:])
        return getattr(mod, names[-1])
