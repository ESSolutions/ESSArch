import six
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Min, Q
from django.shortcuts import _get_queryset
from guardian.models import GroupObjectPermission, UserObjectPermission

from ESSArch_Core.auth.models import Group, GroupGenericObjects, GroupMember, GroupMemberRole

ORGANIZATION_TYPE = 'organization'


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


def get_user_groups(user):
    top_groups = user.essauth_member.groups.annotate(min_level=Min('level')).filter(level=F('min_level'))
    groups = Group.objects.none()
    for g in top_groups:
        groups |= g.get_descendants(include_self=True)

    return groups


def get_user_roles(user, start_group=None):
    org = user.user_profile.current_organization
    if org is None:
        return GroupMemberRole.objects.none()

    member = user.essauth_member
    if start_group is not None:
        groups = start_group.get_ancestors(include_self=True, ascending=True)
    else:
        groups = org.get_ancestors(include_self=True, ascending=True)
    memberships = GroupMember.objects.filter(group__in=groups, member=member)
    return GroupMemberRole.objects.filter(group_memberships__in=memberships)


def get_objects_for_user(user, klass, perms):
    qs = _get_queryset(klass)

    if not user.is_active or user.is_anonymous:
        return qs.none()

    if user.is_superuser:
        return qs

    if isinstance(perms, six.string_types):
        perms = [perms]

    codenames = set()
    for perm in perms:
        if '.' in perm:
            _, codename = perm.split('.', 1)
        else:
            codename = perm
        codenames.add(codename)

    roles = get_user_roles(user)
    ctype = ContentType.objects.get_for_model(qs.model)

    owned_codenames = []
    if len(codenames):
        owned_codenames = Permission.objects.filter(roles__in=roles).values_list('codename', flat=True)

    role_ids = set()

    org = user.user_profile.current_organization
    if org is not None:
        # Because of UUIDs we have to first save the IDs in
        # memory and then query against that list, see
        # https://stackoverflow.com/questions/50526873/
        if not len(set(codenames).difference(set(owned_codenames))):
            generic_objects = GroupGenericObjects.objects.filter(content_type=ctype, group=org)
            role_ids = set(generic_objects.values_list('object_id', flat=True))

    groups = get_user_groups(user)
    group_ids = set(GroupObjectPermission.objects.filter(group__essauth_group__in=groups,
                                                         permission__codename__in=codenames)
                                                 .values_list('object_pk', flat=True))

    user_ids = set(UserObjectPermission.objects.filter(user=user, permission__codename__in=codenames)
                                               .values_list('object_pk', flat=True))

    all_ids = role_ids | group_ids | user_ids
    return qs.filter(pk__in=all_ids)
