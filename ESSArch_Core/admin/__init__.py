from nested_inline.admin import NestedStackedInline

default_app_config = 'ESSArch_Core.admin.apps.AdminConfig'


class NestedStackedInlineWithoutHeader(NestedStackedInline):
    template = "essadmin/edit_inline/stacked-nested-without-header.html"
