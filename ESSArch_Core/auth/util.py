from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models import (
    CharField,
    Exists,
    F,
    Min,
    OuterRef,
    Q,
    UUIDField,
    Value,
)
from django.db.models.functions import Cast, Replace
from django.shortcuts import _get_queryset
from guardian.models import GroupObjectPermission, UserObjectPermission

from ESSArch_Core.auth.models import (
    Group,
    GroupGenericObjects,
    GroupMember,
    GroupMemberRole,
)

User = get_user_model()
ORGANIZATION_TYPE = 'organization'


def get_organization_groups(user):
    """
    Gets the organization groups that `user` is part of

    Args:
        user: The user to get groups for
    """

    if user.is_superuser:
        return Group.objects.filter(group_type__codename=ORGANIZATION_TYPE)

    sub_group_filter = Q(
        ~Q(sub_essauth_group_set__group_type__codename=ORGANIZATION_TYPE) &
        Q(sub_essauth_group_set__django_group__user=user)
    )
    return Group.objects.filter(Q(Q(sub_group_filter) | Q(django_group__user=user)),
                                group_type__codename=ORGANIZATION_TYPE).distinct()


def users_in_organization(user):
    if user.is_superuser:
        return User.objects.all()

    groups = get_user_groups(user)
    return User.objects.filter(essauth_member__essauth_groups__in=groups)


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
    # TODO: Fixed in Django 3
    if connection.features.has_native_uuid_field:
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
    role_ids = GroupGenericObjects.objects.none()

    org = user.user_profile.current_organization
    if org is not None:
        # Because of UUIDs we have to first save the IDs in
        # memory and then query against that list, see
        # https://stackoverflow.com/questions/50526873/
        # Fixed in Django 3 (hopefully)

        orgs = []

        for org_descendant in org.get_descendants(include_self=True):
            roles = GroupMemberRole.objects.filter(
                group_memberships__group__in=org_descendant.get_ancestors(include_self=True),
                group_memberships__member=user.essauth_member,
            )
            role_perms_codenames = set(Permission.objects.filter(roles__in=roles).values_list('codename', flat=True))
            if not len(set(codenames).difference(set(role_perms_codenames))):
                orgs.append(org_descendant)

        role_ids = GroupGenericObjects.objects.filter(content_type=ctype, group__in=orgs)

    groups = get_user_groups(user)
    grp_filter_kwargs = {
        'content_type': ctype,
    }
    if len(groups) > 0:
        grp_filter_kwargs['group__essauth_group__in'] = groups
    if len(codenames) > 0:
        grp_filter_kwargs['permission__codename__in'] = codenames
    else:
        grp_filter_kwargs['permission__codename__isnull'] = True
    group_ids = GroupObjectPermission.objects.filter(**grp_filter_kwargs)

    user_filter_kwargs = {
        'user': user,
        'content_type': ctype,
    }
    if len(codenames) > 0:
        user_filter_kwargs['permission__codename__in'] = codenames
    else:
        user_filter_kwargs['permission__codename__isnull'] = True
    user_ids = UserObjectPermission.objects.filter(**user_filter_kwargs)

    ids_with_no_auth = qs.model.objects.none()

    if include_no_auth_objs:
        ids_with_no_auth = qs.annotate(casted_pk=Cast('pk', CharField())).exclude(
            casted_pk__in=UserObjectPermission.objects.filter(content_type=ctype).annotate(
                cleaned_pk=replace_func('object_pk', qs.model._meta.pk)
            ).values('cleaned_pk')
        ).exclude(
            casted_pk__in=GroupObjectPermission.objects.filter(content_type=ctype).annotate(
                cleaned_pk=replace_func('object_pk', qs.model._meta.pk)
            ).values('cleaned_pk')
        ).exclude(
            casted_pk__in=GroupGenericObjects.objects.filter(content_type=ctype).annotate(
                cleaned_pk=replace_func('object_id', qs.model._meta.pk)
            ).values('cleaned_pk')
        )

    role_ids = role_ids.annotate(
        cleaned_pk=replace_func('object_id', qs.model._meta.pk)
    )
    group_ids = group_ids.annotate(
        cleaned_pk=replace_func('object_pk', qs.model._meta.pk)
    )
    user_ids = user_ids.annotate(
        cleaned_pk=replace_func('object_pk', qs.model._meta.pk)
    )

    if connection.vendor == 'microsoft':
        qs = qs.annotate(
            cleaned_id=Cast('pk', CharField()),
        ).filter(Q(
            Q(cleaned_id__in=role_ids.values('cleaned_pk')) |
            Q(cleaned_id__in=group_ids.values('cleaned_pk')) |
            Q(cleaned_id__in=user_ids.values('cleaned_pk'))
        ))
    else:
        qs = qs.annotate(
            cleaned_id=Cast('pk', CharField()),
            role_exists=Exists(
                role_ids.filter(cleaned_pk=OuterRef('cleaned_id'))
            ),
            grp_exists=Exists(
                group_ids.filter(cleaned_pk=OuterRef('cleaned_id'))
            ),
            user_exists=Exists(
                user_ids.filter(cleaned_pk=OuterRef('cleaned_id'))
            ),
        ).filter(Q(
            Q(role_exists=True) |
            Q(grp_exists=True) |
            Q(user_exists=True)
        ))
    return qs | ids_with_no_auth
