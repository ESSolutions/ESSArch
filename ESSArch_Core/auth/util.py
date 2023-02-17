from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models import F, Min, Model, Q, UUIDField, Value
from django.db.models.functions import Replace
from django.db.models.query import QuerySet
from guardian.ctypes import get_content_type
from guardian.shortcuts import (
    _handle_pk_field,
    get_objects_for_user as get_objects_for_user_guardian,
)
from guardian.utils import get_group_obj_perms_model, get_user_obj_perms_model

from ESSArch_Core.auth.models import Group, GroupMember, GroupMemberRole

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


def get_grp_objs_model(obj, base_cls, generic_cls):
    """
    Return the matching object permission model for the obj class
    Defaults to returning the generic object permission when
    no direct foreignkey is defined or obj is None
    """
    # Default to the generic object permission model
    # when None obj is provided
    if obj is None:
        return generic_cls

    if isinstance(obj, Model):
        obj = obj.__class__

    fields = (f for f in obj._meta.get_fields()
              if (f.one_to_many or f.one_to_one) and f.auto_created)

    for attr in fields:
        model = getattr(attr, 'related_model', None)
        if (model and issubclass(model, base_cls) and
                model is not generic_cls and getattr(model, 'enabled', True)):
            # if model is generic one it would be returned anyway
            if not model.objects.is_generic():
                # make sure that content_object's content_type is same as
                # the one of given obj
                fk = model._meta.get_field('content_object')
                if get_content_type(obj) == get_content_type(fk.remote_field.model):
                    return model
    return generic_cls


def get_group_objs_model(obj=None):
    """
    Returns model class that connects given ``obj`` and Group class.
    If obj is not specified, then group generic object permission model
    returned is determined byt the guardian setting 'GROUP_OBJ_PERMS_MODEL'.
    """
    from ESSArch_Core.auth.models import GroupGenericObjects, GroupObjectsBase
    return get_grp_objs_model(obj, GroupObjectsBase, GroupGenericObjects)


def get_objects_for_user(user, klass, perms=None, current_organization=True, include_no_auth_objs=True):
    if not perms:
        if isinstance(klass, QuerySet):
            perms = 'view_{}'.format(klass.model._meta.model_name)
        else:
            perms = 'view_{}'.format(klass._meta.model_name)

    queryset = get_objects_for_user_guardian(user, perms, klass)

    if current_organization and not user.is_superuser:
        if isinstance(current_organization, Group):
            org = current_organization
        else:
            org = user.user_profile.current_organization

        if org is not None:
            if isinstance(perms, str):
                perms = [perms]

            codenames = set()
            for perm in perms:
                if '.' in perm:
                    _, codename = perm.split('.', 1)
                else:
                    codename = perm
                codenames.add(codename)

            group_objs_model = get_group_objs_model(queryset.model)
            groups_objs_queryset = group_objs_model.objects.none()
            orgs = []
            ctype = None

            for org_descendant in org.get_descendants(include_self=True):
                roles = GroupMemberRole.objects.filter(
                    group_memberships__group__in=org_descendant.get_ancestors(include_self=True),
                    group_memberships__member=user.essauth_member,
                )
                role_perms_codenames = set(Permission.objects.filter(
                    roles__in=roles).values_list('codename', flat=True))
                if not len(set(codenames).difference(set(role_perms_codenames))):
                    orgs.append(org_descendant)

            if group_objs_model.objects.is_generic():
                field_pk = 'object_id'
                ctype = ContentType.objects.get_for_model(queryset.model)
                groups_objs_total_queryset = group_objs_model.objects.filter(content_type=ctype)
                groups_objs_queryset = groups_objs_total_queryset.filter(group__in=orgs)
                handle_pk_field = _handle_pk_field(queryset)
                if handle_pk_field is not None:
                    groups_objs_queryset = groups_objs_queryset.annotate(obj_pk=handle_pk_field(expression=field_pk))
                    if include_no_auth_objs:
                        groups_objs_total_queryset = groups_objs_total_queryset.annotate(
                            obj_pk=handle_pk_field(expression=field_pk))
                    field_pk = 'obj_pk'
            else:
                field_pk = 'content_object_id'
                groups_objs_total_queryset = group_objs_model.objects.all()
                groups_objs_queryset = groups_objs_total_queryset.filter(group__in=orgs)
            values = groups_objs_queryset.values_list(field_pk, flat=True)

            if include_no_auth_objs:
                user_model = get_user_obj_perms_model(queryset.model)
                if user_model.objects.is_generic():
                    user_field_pk = 'object_pk'
                    if ctype is None:
                        ctype = ContentType.objects.get_for_model(queryset.model)
                    user_obj_perms_queryset = user_model.objects.filter(content_type=ctype)
                    handle_pk_field = _handle_pk_field(queryset)
                    if handle_pk_field is not None:
                        user_obj_perms_queryset = user_obj_perms_queryset.annotate(
                            obj_pk=handle_pk_field(expression=user_field_pk))
                        user_field_pk = 'obj_pk'
                else:
                    user_field_pk = 'content_object_id'
                    user_obj_perms_queryset = user_model.objects.all()

                group_model = get_group_obj_perms_model(queryset.model)
                if group_model.objects.is_generic():
                    group_field_pk = 'object_pk'
                    if ctype is None:
                        ctype = ContentType.objects.get_for_model(queryset.model)
                    groups_obj_perms_queryset = group_model.objects.filter(content_type=ctype)
                    handle_pk_field = _handle_pk_field(queryset)
                    if handle_pk_field is not None:
                        groups_obj_perms_queryset = groups_obj_perms_queryset.annotate(
                            obj_pk=handle_pk_field(expression=group_field_pk))
                        group_field_pk = 'obj_pk'
                else:
                    group_field_pk = 'content_object_id'
                    groups_obj_perms_queryset = group_model.objects.all()

                ids_with_no_auth = queryset.exclude(
                    pk__in=user_obj_perms_queryset.values_list(user_field_pk, flat=True)
                ).exclude(
                    pk__in=user_obj_perms_queryset.values_list(group_field_pk, flat=True)
                ).exclude(
                    pk__in=groups_objs_total_queryset.values_list(field_pk, flat=True)
                )

                queryset = queryset.filter(Q(pk__in=values) | Q(pk__in=ids_with_no_auth))
            else:
                queryset = queryset.filter(pk__in=values)
    return queryset
