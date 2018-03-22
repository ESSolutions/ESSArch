from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as DjangoGroup, Permission
from django.db.models import Q, Subquery

from ESSArch_Core.auth.models import Group

from rest_framework import exceptions

ORGANIZATION_TYPE = 'organization'


def get_membership_descendants(group, user):
    """
    Gets the non organization groups (+ the group with id `group_id`) directly
    under `group_id` if `group_id` is of type "organization" and `user` is a
    member of `group_id`. If not, only the descendants which are not of type
    "organization" and that `user` is member of are returned.

    Args:
        group_id: The id of the "base" group
        user: The user to check membership for
    """

    if group is None:
        return Group.objects.none()

    descendants = group.get_descendants(include_self=True).filter(level__in=[group.level, group.level+1])

    is_organization = getattr(group.group_type, 'codename', None) == ORGANIZATION_TYPE
    is_member = group.django_group.user_set.filter(id=user.id).exists()

    if not (is_organization and is_member):
        descendants = descendants.exclude(group_type__codename=ORGANIZATION_TYPE).filter(django_group__user__id=user.id)

    return descendants


def get_organization_groups(user):
    """
    Gets the organization groups that `user` is part of

    Args:
        user: The user to get groups for
    """

    sub_group_filter = Q(
        ~Q(sub_essauth_group_set__group_type__codename=ORGANIZATION_TYPE) &
        Q(sub_essauth_group_set__django_group__user=user)
    )
    return Group.objects.filter(Q(Q(sub_group_filter) | Q(django_group__user=user)),
                                group_type__codename=ORGANIZATION_TYPE).distinct()


def get_permission_objs(user):
    perms = Permission.objects.none()

    if not user.is_active or user.is_anonymous:
        return perms

    if user.is_superuser:
        return Permission.objects.all()

    org = user.user_profile.current_organization
    if org is not None:
        groups = get_membership_descendants(org, user)
        perms = Permission.objects.filter(group__in=Subquery(groups.values('django_group__id')))


    # non-groups_manager group permissions
    user_groups_field = get_user_model()._meta.get_field('groups')
    user_groups_query = 'group__%s' % user_groups_field.related_query_name()
    perms |= Permission.objects.filter(group__group=None, **{user_groups_query: user})

    perms |= user.user_permissions.all()
    return perms.distinct()


def get_permission_set(user):
    perms = get_permission_objs(user).values_list('content_type__app_label', 'codename').order_by()
    return {'%s.%s' % (ct, name) for ct, name in perms}
