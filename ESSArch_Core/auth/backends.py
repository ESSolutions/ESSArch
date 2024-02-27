import logging
from itertools import chain

from django.contrib.auth.models import Permission
from django.core.exceptions import MultipleObjectsReturned
from django.db.models import F, Value
from django.db.models.functions import Concat

from ESSArch_Core.auth.util import get_group_objs_model, get_user_roles

logger = logging.getLogger('essarch.auth')


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

    return perms


class GroupRoleBackend:
    supports_object_permissions = True

    def authenticate(self, *args, **kwargs):
        return None

    def get_all_permissions(self, user_obj, obj=None):
        go_obj = None

        if obj is not None:
            group_objs_model = get_group_objs_model(obj)
            try:
                go_obj = group_objs_model.objects.get_organization(obj)
            except MultipleObjectsReturned as e:
                go_objs = group_objs_model.objects.get_organization(obj, list=True)
                group_list = [x.group for x in go_objs]
                message_info = 'Expected one GroupObjects for {} {} but got multiple go_objs \
with folowing groups: {}'.format(obj._meta.model_name, obj, group_list)
                logger.warning(message_info)
                raise e
            except group_objs_model.DoesNotExist:
                return set()

            full_name = F('codename')
        else:
            full_name = Concat(F('content_type__app_label'), Value('.'), F('codename'))

        return list(set(chain(
            *_get_permission_objs(user_obj, go_obj).annotate(full_name=full_name).values_list('full_name')
        )))

    def has_perm(self, user_obj, perm, obj=None):
        if '.' in perm and obj is not None:
            app_label, perm = perm.split('.')
        return perm in self.get_all_permissions(user_obj, obj=obj)

    def has_module_perms(self, user_obj, app_label):
        return user_obj.is_active and any(
            perm[:perm.index('.')] == app_label
            for perm in self.get_all_permissions(user_obj)
        )
