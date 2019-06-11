from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models import CharField, F, Min, Q, UUIDField, Value
from django.db.models.functions import Cast, Replace
from django.shortcuts import _get_queryset
from guardian.models import GroupObjectPermission, UserObjectPermission

from ESSArch_Core.auth.models import (
    Group,
    GroupGenericObjects,
    GroupMember,
    GroupMemberRole,
)

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


def replace_func(field, field_type):
    if connection.vendor == 'postgresql':
        return F(field)

    if isinstance(field_type, UUIDField):
        return Replace(field, Value('-'), Value(''))

    return F(field)


def get_objects_for_user(user, klass, perms=None, include_no_auth_objs=True):
    qs = _get_queryset(klass)

    if perms is None:
        perms = []

    if not user.is_active or user.is_anonymous:
        return qs.none()

    if user.is_superuser:
        return qs

    if isinstance(perms, str):
        perms = [perms]

    codenames = set()
    for perm in perms:
        if '.' in perm:
            _, codename = perm.split('.', 1)
        else:
            codename = perm
        codenames.add(codename)

    ctype = ContentType.objects.get_for_model(qs.model)
    role_ids = set()

    org = user.user_profile.current_organization
    if org is not None:
        # Because of UUIDs we have to first save the IDs in
        # memory and then query against that list, see
        # https://stackoverflow.com/questions/50526873/
        for org_descendant in org.get_descendants(include_self=True):
            roles = GroupMemberRole.objects.filter(
                group_memberships__group__in=org_descendant.get_ancestors(include_self=True),
                group_memberships__member=user.essauth_member,
            )
            role_perms_codenames = set(Permission.objects.filter(roles__in=roles).values_list('codename', flat=True))
            if not len(set(codenames).difference(set(role_perms_codenames))):
                generic_objects = GroupGenericObjects.objects.filter(content_type=ctype, group=org_descendant)
                role_ids |= set(generic_objects.values_list('object_id', flat=True))

    groups = get_user_groups(user)
    group_ids = set(GroupObjectPermission.objects.filter(
        group__essauth_group__in=groups, permission__codename__in=codenames, content_type=ctype
    ).values_list('object_pk', flat=True))

    user_ids = set(UserObjectPermission.objects.filter(
        user=user, permission__codename__in=codenames, content_type=ctype
    ).values_list('object_pk', flat=True))

    all_ids = role_ids | group_ids | user_ids

    if include_no_auth_objs:
        ids_with_no_auth = set(qs.annotate(casted_pk=Cast('pk', CharField()))
                               .exclude(
                                   casted_pk__in=UserObjectPermission.objects.filter(content_type=ctype).annotate(
                                       cleaned_pk=replace_func('object_pk', qs.model._meta.pk)
                                   ).values('cleaned_pk'))
                               .exclude(
                                   casted_pk__in=GroupObjectPermission.objects.filter(content_type=ctype).annotate(
                                       cleaned_pk=replace_func('object_pk', qs.model._meta.pk)
                                   ).values('cleaned_pk'))
                               .exclude(
                                   casted_pk__in=GroupGenericObjects.objects.filter(content_type=ctype).annotate(
                                       cleaned_pk=replace_func('object_id', qs.model._meta.pk)
                                   ).values('cleaned_pk'))
                               .values_list('pk', flat=True))

        all_ids |= ids_with_no_auth
    return qs.filter(pk__in=all_ids)
