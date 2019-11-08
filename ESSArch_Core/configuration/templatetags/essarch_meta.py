from django import template
from django.conf import settings

from ESSArch_Core._version import get_versions

register = template.Library()


@register.simple_tag
def essarch_version():
    return get_versions()['version']


@register.simple_tag
def essarch_project_name():
    return settings.PROJECT_NAME


@register.simple_tag
def essarch_project_shortname():
    return settings.PROJECT_SHORTNAME
