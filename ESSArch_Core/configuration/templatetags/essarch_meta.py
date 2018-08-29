from django import template
from _version import get_versions

register = template.Library()


@register.simple_tag
def essarch_version():
    return get_versions()['version']
