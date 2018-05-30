from itertools import chain

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Value
from django.db.models.functions import Concat

from ESSArch_Core.auth.models import GroupGenericObjects
from ESSArch_Core.auth.util import get_user_groups, get_user_roles


def _get_permission_objs(user, obj=None):
    perms = Permission.objects.none()
    org = user.user_profile.current_organization
    if org is not None:
        if obj is not None:
            start_grp = obj.group
        else:
            start_grp = org

        roles = get_user_roles(user, start_grp)
        perms = Permission.objects.filter(roles__in=roles)

    return perms.distinct()


class GroupRoleBackend(object):
    supports_object_permissions = True

    def authenticate(self, *args, **kwargs):
        return None

    def get_all_permissions(self, user_obj, obj=None):
        groups = get_user_groups(user_obj)

        if obj is not None:
            ctype = ContentType.objects.get_for_model(obj)
            try:
                obj = GroupGenericObjects.objects.get(content_type=ctype, object_id=obj.pk, group__in=groups)
            except GroupGenericObjects.DoesNotExist:
                return set()

            full_name = F('codename')
        else:
            full_name = Concat(F('content_type__app_label'), Value('.'), F('codename'))

        return list(set(chain(*_get_permission_objs(user_obj, obj).annotate(full_name=full_name).values_list('full_name'))))

    def has_perm(self, user_obj, perm, obj=None):
        return perm in self.get_all_permissions(user_obj, obj=obj)

