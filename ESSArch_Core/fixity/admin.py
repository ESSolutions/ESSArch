from django.contrib import admin

from ESSArch_Core.fixity.models import ConversionTool


class ConversionToolAdmin(admin.ModelAdmin):
    fields = ('name', 'type', 'enabled', 'path', 'cmd', 'form')
    list_display = ('name', 'type', 'enabled')


admin.site.register(ConversionTool, ConversionToolAdmin)
