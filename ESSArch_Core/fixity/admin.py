from django.contrib import admin
from django_json_widget.widgets import JSONEditorWidget
from django.db import models

from ESSArch_Core.fixity.models import ActionTool


class ActionToolAdmin(admin.ModelAdmin):
    fields = ('name', 'enabled', 'type', 'environment', 'file_processing', 'delete_original', 'path', 'cmd', 'form')
    list_display = ('name', 'enabled', 'type', 'environment', 'file_processing', 'delete_original')
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }


admin.site.register(ActionTool, ActionToolAdmin)
