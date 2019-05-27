from rest_framework import permissions

from ESSArch_Core.tags.models import Structure


class AddStructureUnit(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method not in ('POST') or request._request.method == "OPTIONS":
            return True

        if not 'parent_lookup_structure' in request.parser_context['kwargs']:
            return False

        structure = request.parser_context['kwargs']['parent_lookup_structure']
        structure = Structure.objects.get(pk=structure)

        if structure.is_template:
            return True

        return request.user.has_perm('tags.add_structureunit_instance')


class ChangeStructureUnit(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method not in ('PATCH', 'PUT') or request._request.method == "OPTIONS":
            return True

        if obj.structure.is_template:
            return True

        data = request.data.copy()
        perms = []

        if 'parent' in data:
            perms.append('tags.move_structureunit_instance')

        data.pop('parent', None)

        if len(data.keys()) > 1:  # always contains structure
            perms.append('tags.change_structureunit_instance')

        return request.user.has_perms(perms)


class DeleteStructureUnit(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method != 'DELETE':
            return True

        if obj.structure.is_template:
            return True

        return request.user.has_perm('tags.delete_structureunit_instance')
