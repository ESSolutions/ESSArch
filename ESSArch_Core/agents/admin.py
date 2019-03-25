from django.contrib import admin

from ESSArch_Core.agents.models import (
    AgentIdentifierType,
    AgentNameType,
    AgentNoteType,
    AgentPlaceType,
    AgentRelationType,
    AgentType,
    AuthorityType,
    MainAgentType,
)


admin.site.register(AgentIdentifierType)
admin.site.register(AgentNameType)
admin.site.register(AgentNoteType)
admin.site.register(AgentPlaceType)
admin.site.register(AgentRelationType)
admin.site.register(AgentType)
admin.site.register(AuthorityType)
admin.site.register(MainAgentType)
