from rest_framework.permissions import BasePermission


class SearchPermissions(BasePermission):
    def has_permission(self, request, view):
        if request.user.has_perm('tags.search'):
            return True

        return False
