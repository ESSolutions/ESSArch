from django.db.models import Q

from groups_manager.models import Group

from rest_framework import exceptions

ORGANIZATION_TYPE = 'organization'


def get_membership_descendants(group_id, user):
    """
    Gets the non organization groups (+ the group with id `group_id`) directly
    under `group_id` if `group_id` is of type "organization" and `user` is a
    member of `group_id`. If not, only the descendants which are not of type
    "organization" and that `user` is member of are returned.

    Args:
        group_id: The id of the "base" group
        user: The user to check membership for
    """

    try:
        group = Group.objects.get(pk=group_id)
    except Group.DoesNotExist:
        raise exceptions.ParseError('Invalid group')

    descendants = group.get_descendants(include_self=True).filter(level__in=[group.level, group.level+1])

    if not (getattr(group.group_type, 'codename') == ORGANIZATION_TYPE and group.group_members.filter(django_user=user).exists()):
        descendants = descendants.exclude(group_type__codename=ORGANIZATION_TYPE).filter(group_members__django_user=user)

    return descendants


def get_organization_groups(user):
    """
    Gets the organization groups that `user` is part of

    Args:
        user: The user to get groups for
    """

    member = user.groups_manager_member_set.first()

    sub_group_filter = Q(
        ~Q(sub_groups_manager_group_set__group_type__codename=ORGANIZATION_TYPE) &
        Q(sub_groups_manager_group_set__group_members=member)
    )
    return Group.objects.filter(Q(Q(sub_group_filter) | Q(group_members=member)),
                                group_type__codename=ORGANIZATION_TYPE).distinct()
