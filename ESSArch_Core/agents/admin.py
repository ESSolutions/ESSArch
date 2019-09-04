from django.contrib import admin

from ESSArch_Core.agents.models import (
    AgentIdentifierType,
    AgentNameType,
    AgentNoteType,
    AgentPlaceType,
    AgentRelationType,
    AgentTagLinkRelationType,
    AgentType,
    AuthorityType,
    MainAgentType,
    RefCode,
)


class AgentNoteTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'history')


class AgentNameTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'authority')


class AgentRelationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'mirrored_type')


admin.site.register(AgentIdentifierType)
admin.site.register(AgentNameType, AgentNameTypeAdmin)
admin.site.register(AgentNoteType, AgentNoteTypeAdmin)
admin.site.register(AgentPlaceType)
admin.site.register(AgentRelationType, AgentRelationTypeAdmin)
admin.site.register(AgentTagLinkRelationType)
admin.site.register(AgentType)
admin.site.register(AuthorityType)
admin.site.register(MainAgentType)
admin.site.register(RefCode)
