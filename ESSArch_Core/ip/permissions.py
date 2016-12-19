from rest_framework import permissions

class IsResponsibleOrReadOnly(permissions.BasePermission):
    message = "You are not responsible for this IP"

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.Responsible == request.user
