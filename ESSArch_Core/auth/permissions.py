from rest_framework.permissions import DjangoModelPermissions


class ActionPermissions(DjangoModelPermissions):
    """
    Adds permission based on the action (class method) instead of the default HTTP method.

    """
    # Map actions into required permission codes.
    perms_map = {
        'list': [],
        'retrieve': [],
        'create': ['%(app_label)s.add_%(model_name)s'],
        'update': ['%(app_label)s.change_%(model_name)s'],
        'partial_update': ['%(app_label)s.change_%(model_name)s'],
        'destroy': ['%(app_label)s.delete_%(model_name)s'],
    }

    def get_required_permissions(self, method, model_cls):
        """
        Given a model and a called method, return the list of permission
        codes that the user is required to have.
        """
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name
        }

        if method not in self.perms_map:
            return []

        return [perm % kwargs for perm in self.perms_map[method]]

    def has_permission(self, request, view):
        # Workaround to ensure DjangoModelPermissions are not applied
        # to the root view when using DefaultRouter.
        if getattr(view, '_ignore_model_permissions', False):
            return True

        if not request.user or (not request.user.is_authenticated and self.authenticated_users_only):
            return False

        queryset = self._queryset(view)
        if not hasattr(view, 'action'):
            raise Exception("View should have an action defined in django-rest-framework.ModelViewSet")
        perms = self.get_required_permissions(view.action, queryset.model)

        return request.user.has_perms(perms)
