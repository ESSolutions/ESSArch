from django.core.cache import cache
from django.utils.functional import wraps
from redis.exceptions import LockError
from rest_framework.generics import get_object_or_404

from ESSArch_Core.exceptions import Conflict


def lock_obj(timeout=None, sleep=0.1, blocking_timeout=None):
    def decorator(view_func):
        def _wrapped_view(view, request, *args, **kwargs):
            obj = None

            if hasattr(view, 'get_queryset'):
                pk = kwargs.get('pk')
                model = view.get_queryset().model
                if model and pk is not None:
                    obj = get_object_or_404(model, pk=pk)

            if obj is not None:
                try:
                    with cache.lock('%s-%s' % (obj.__class__.__name__, obj.pk),
                                    timeout=timeout, sleep=sleep, blocking_timeout=blocking_timeout):
                        return view_func(view, request, *args, **kwargs)
                except LockError:
                    raise Conflict('Resource is locked')
            else:
                return view_func(view, request, *args, **kwargs)

        return wraps(view_func)(_wrapped_view)
    return decorator
