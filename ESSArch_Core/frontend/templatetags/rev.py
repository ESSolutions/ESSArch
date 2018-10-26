import json
import os

from django import template
from django.conf import settings
from django.templatetags.static import StaticNode


def _get_mapping():
    """
    Finds and loads gulp's rev-manifest.json file. Use DJANGO_GULP_REV_PATH to
    set the path.
    """

    manifest_path = getattr(settings,
        'DJANGO_GULP_REV_PATH',
        os.path.join(getattr(settings, 'STATIC_ROOT', ''), 'rev-manifest.json'))

    try:
        with open(manifest_path) as manifest_file:
            return json.load(manifest_file)
    except IOError:
        return None


def _create_url(path, original):
    mapping = _get_mapping()
    if mapping:
        if path in mapping:
            return original.replace(path, mapping[path])
        return original
    else:
        return ''


def static_rev(path):
    """
    Modified version of static_rev from gulp_rev which ignores debug mode
    """

    static_path = StaticNode.handle_simple(path)
    basename = os.path.basename(path)
    return _create_url(basename, static_path)


register = template.Library()
register.simple_tag(static_rev, name='rev')
