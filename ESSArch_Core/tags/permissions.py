from rest_framework import permissions
from rest_framework.permissions import BasePermission

from ESSArch_Core.tags.models import Structure


class SearchPermissions(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('tags.search')


class AddStructureUnit(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method not in ('POST') or request._request.method == "OPTIONS":
            return True

        if 'parent_lookup_structure' not in request.parser_context['kwargs']:
            return False

        structure = request.parser_context['kwargs']['parent_lookup_structure']
        structure = Structure.objects.get(pk=structure)

        is_template = structure.is_template
        add_perm = 'tags.add_structureunit' if is_template else 'tags.add_structureunit_instance'

        return request.user.has_perm(add_perm)


class ChangeStructureUnit(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method not in ('PATCH', 'PUT') or request._request.method == "OPTIONS":
            return True

        is_template = obj.structure.is_template

        change_perm = 'tags.change_structureunit' if is_template else 'tags.change_structureunit_instance'

        if is_template:
            return request.user.has_perm(change_perm)

        perms = []
        data = request.data.copy()

        if 'parent' in data and not is_template:
            perms.append('tags.move_structureunit_instance')

        data.pop('parent', None)

        if len(data.keys()) > 1:  # always contains structure
            perms.append(change_perm)

        return request.user.has_perms(perms)


class DeleteStructureUnit(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method != 'DELETE':
            return True

        is_template = obj.structure.is_template
        delete_perm = 'tags.delete_structureunit' if is_template else 'tags.delete_structureunit_instance'

        return request.user.has_perm(delete_perm)
