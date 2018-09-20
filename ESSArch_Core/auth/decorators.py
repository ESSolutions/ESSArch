import six
from django.shortcuts import get_object_or_404
from django.utils.functional import wraps
from rest_framework import exceptions


def permission_required_or_403(perms, accept_global_perms=True):
    if isinstance(perms, six.string_types):
        perms = [perms]

    def decorator(view_func):
        def _wrapped_view(view, request, *args, **kwargs):
            pk = kwargs.get('pk')
            obj = None

            model = view.get_queryset().model
            if model and pk is not None:
                obj = get_object_or_404(model, pk=pk)

            has_permissions = False
            if accept_global_perms:
                has_permissions = all(request.user.has_perm(perm) for perm in perms)

            if not has_permissions:
                has_permissions = all(request.user.has_perm(perm, obj) for perm in perms)

            if not has_permissions:
                raise exceptions.PermissionDenied

            return view_func(view, request, *args, **kwargs)

        return wraps(view_func)(_wrapped_view)
    return decorator
