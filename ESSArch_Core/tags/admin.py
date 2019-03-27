from django.contrib import admin

from ESSArch_Core.tags.models import (
    StructureType,
    StructureUnitType,
    TagVersionType,
)


admin.site.register(StructureType)
admin.site.register(StructureUnitType)
admin.site.register(TagVersionType)
