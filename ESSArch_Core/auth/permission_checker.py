from itertools import chain

from django.contrib.auth.models import Permission
from django.db.models import Prefetch
from django.utils.encoding import force_str
from guardian.core import (
    ObjectPermissionChecker as GuardianObjectPermissionChecker,
    _get_pks_model_and_ctype,
)

from ESSArch_Core.auth.models import GroupMember
from ESSArch_Core.auth.util import get_group_objs_model, get_user_groups


class ObjectPermissionChecker(GuardianObjectPermissionChecker):
    def prefetch_perms(self, objects):
        """
        Prefetches the permissions for objects in ``objects`` and puts them in the cache.

        :param objects: Iterable of Django model objects

        """

        if self.user and not self.user.is_active:
            return []

        pks, model, ctype = _get_pks_model_and_ctype(objects)

        if self.user and self.user.is_superuser:
            perms = list(chain(
                *Permission.objects.filter(content_type=ctype).values_list("codename")))

            for pk in pks:
                key = (ctype.id, force_str(pk))
                self._obj_perms_cache[key] = perms

            return True

        from_guardian = super().prefetch_perms(objects)

        if not self.user:
            return from_guardian

        groups = get_user_groups(self.user)
        group_objs_model = get_group_objs_model(model)
        if group_objs_model.objects.is_generic():
            generic_objs = group_objs_model.objects.select_related('group').prefetch_related(
                Prefetch(
                    'group__ascendants__group_membership',
                    queryset=GroupMember.objects.filter(
                        member__django_user=self.user
                    ).prefetch_related('roles__permissions')
                ),
                Prefetch(
                    'group__group_membership',
                    queryset=GroupMember.objects.filter(
                        member__django_user=self.user
                    ).prefetch_related('roles__permissions')
                ),
            ).filter(
                content_type=ctype, object_id__in=pks, group__in=groups
            )
        else:
            generic_objs = group_objs_model.objects.select_related('group').prefetch_related(
                Prefetch(
                    'group__ascendants__group_membership',
                    queryset=GroupMember.objects.filter(
                        member__django_user=self.user
                    ).prefetch_related('roles__permissions')
                ),
                Prefetch(
                    'group__group_membership',
                    queryset=GroupMember.objects.filter(
                        member__django_user=self.user
                    ).prefetch_related('roles__permissions')
                ),
            ).filter(
                content_object_id__in=pks, group__in=groups
            )

        # print('generic_objs: {}, count: {}'.format(generic_objs, generic_objs.count()))
        for obj in objects:
            key = self.get_local_cache_key(obj)
            if key not in self._obj_perms_cache:
                self._obj_perms_cache[key] = []

        for generic_obj in generic_objs:
            for ascendant in generic_obj.group.ascendants.all():
                for membership in ascendant.group_membership.all():
                    for role in membership.roles.all():
                        for perm in role.permissions.all():
                            # TODO: add permission to cache for object referenced by generic_obj (right?)
                            if group_objs_model.objects.is_generic():
                                key = (ctype.id, force_str(generic_obj.object_id))
                            else:
                                key = (ctype.id, force_str(generic_obj.content_object_id))
                            # print('add ascendants perm: {}, key: {}'.format(perm.codename, key))
                            self._obj_perms_cache[key].append(perm.codename)

            for membership in generic_obj.group.group_membership.all():
                for role in membership.roles.all():
                    for perm in role.permissions.all():
                        # TODO: add permission to cache for object referenced by generic_obj (right?)
                        if group_objs_model.objects.is_generic():
                            key = (ctype.id, force_str(generic_obj.object_id))
                        else:
                            key = (ctype.id, force_str(generic_obj.content_object_id))
                        # print('add group_membership perm: {}, key: {}'.format(perm.codename, key))
                        self._obj_perms_cache[key].append(perm.codename)
