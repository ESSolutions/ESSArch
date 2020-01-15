from django.utils.functional import wraps
from rest_framework import exceptions

from ESSArch_Core.configuration.models import Feature


def feature_enabled_or_404(name):
    def decorator(view_func):
        def _wrapped_view(view, request, *args, **kwargs):
            try:
                Feature.objects.get(name=name, enabled=True)
            except Feature.DoesNotExist:
                raise exceptions.NotFound
            else:
                return view_func(view, request, *args, **kwargs)
        return wraps(view_func)(_wrapped_view)
    return decorator
