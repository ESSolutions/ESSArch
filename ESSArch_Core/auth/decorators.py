from django.contrib.auth import get_user_model
from django.utils.functional import wraps
from rest_framework import exceptions
from rest_framework.generics import get_object_or_404

User = get_user_model()


def permission_required_or_403(perms, accept_global_perms=True):
    if isinstance(perms, str):
        perms = [perms]

    def decorator(view_func):
        def _wrapped_view(view, request, *args, **kwargs):
            obj = None

            if hasattr(view, 'get_queryset'):
                pk = kwargs.get('pk')
                model = view.get_queryset().model
                if model and pk is not None:
                    obj = get_object_or_404(model, pk=pk)

            # clear permission cache
            # see https://docs.djangoproject.com/en/stable/topics/auth/default/#permission-caching
            user = User.objects.get(pk=request.user.pk)

            has_permissions = False
            if accept_global_perms:
                has_permissions = all(user.has_perm(perm) for perm in perms)

            if not has_permissions:
                has_permissions = all(user.has_perm(perm, obj) for perm in perms)

            if not has_permissions:
                raise exceptions.PermissionDenied

            return view_func(view, request, *args, **kwargs)

        return wraps(view_func)(_wrapped_view)
    return decorator
