from django import template
from django.templatetags.static import StaticNode
from gulp_rev import production_url

def static_rev(path):
    """
    Modified version of static_rev from gulp_rev which ignores debug mode
    """

    static_path = StaticNode.handle_simple(path)
    return production_url(path, static_path)

register = template.Library()
register.simple_tag(static_rev, name='rev')
