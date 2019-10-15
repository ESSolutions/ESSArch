import os
import uuid

from django import template

register = template.Library()


@register.simple_tag
def uuid4():
    """
    Generates a random version 4 UUID
    """
    return str(uuid.uuid4())


@register.filter(name='path_exists')
def path_exists(path):
    return path if os.path.exists(path) else ''
