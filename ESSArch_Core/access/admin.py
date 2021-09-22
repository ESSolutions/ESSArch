from django.contrib import admin

from ESSArch_Core.access.models import AccessAidType


class AccessAidTypeAdmin(admin.ModelAdmin):
    fields = ('name',)
    list_display = ('name',)


admin.site.register(AccessAidType, AccessAidTypeAdmin)
