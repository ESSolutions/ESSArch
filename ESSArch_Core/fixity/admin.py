from django.contrib import admin

from ESSArch_Core.fixity.models import ActionTool


class ActionToolAdmin(admin.ModelAdmin):
    fields = ('name', 'enabled', 'type', 'environment', 'file_processing', 'path', 'cmd', 'form')
    list_display = ('name', 'enabled', 'type', 'environment', 'file_processing')


admin.site.register(ActionTool, ActionToolAdmin)
