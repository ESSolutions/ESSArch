# -*- coding: UTF-8 -*-

"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Tools for Archive (ETA)
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import django
django.setup()

from django.contrib.auth import get_user_model  # noqa
from django.contrib.auth.models import Permission  # noqa
from groups_manager.models import GroupType  # noqa

from ESSArch_Core.auth.models import Group, GroupMemberRole  # noqa
from ESSArch_Core.configuration.models import Path  # noqa

User = get_user_model()


def installDefaultConfiguration():
    print("Installing users, groups and permissions...")
    installDefaultUsers()
    print("\nInstalling paths...")
    installDefaultPaths()

    return 0


def installDefaultUsers():

    #####################################
    # Groups and permissions
    organization, _ = GroupType.objects.get_or_create(label="organization")
    default_org, _ = Group.objects.get_or_create(name='Default', group_type=organization)

    role_user, _ = GroupMemberRole.objects.get_or_create(codename='user')
    permission_list_user = [
        # ---- app: ip ---- model: informationpackage
        ['view_informationpackage', 'ip', 'informationpackage'],       # Can view information packages
        ['delete_informationpackage', 'ip', 'informationpackage'],  # Can delete Information Package (Ingest)
        ['receive', 'ip', 'informationpackage'],                    # Can receive IP
        ['transfer_sip', 'ip', 'informationpackage'],                    # Can transfer SIP
        # ---- app: WorkflowEngine ---- model: processtask
        # ['can_undo','WorkflowEngine','processtask'],             # Can undo tasks (other)
        # ['can_retry','WorkflowEngine','processtask'],             # Can retry tasks (other)
    ]

    for p in permission_list_user:
        p_obj = Permission.objects.get(
            codename=p[0], content_type__app_label=p[1],
            content_type__model=p[2],
        )
        role_user.permissions.add(p_obj)

    role_admin, _ = GroupMemberRole.objects.get_or_create(codename='admin')
    permission_list_admin = [
        # ---- app: profiles ---- model: submissionagreement
        ['add_submissionagreement', 'profiles', 'submissionagreement'],  # Can add Submission Agreement (Import)
        ['change_submissionagreement', 'profiles', 'submissionagreement'],  # Can change Submission Agreement
        # ---- app: profiles ---- model: profile
        ['add_profile', 'profiles', 'profile'],  # Can add Profile (Import)
        ['change_profile', 'profiles', 'profile'],  # Can change Profile
    ]

    for p in permission_list_admin:
        p_obj = Permission.objects.get(
            codename=p[0], content_type__app_label=p[1],
            content_type__model=p[2],
        )
        role_admin.permissions.add(p_obj)

    role_sysadmin, _ = GroupMemberRole.objects.get_or_create(codename='sysadmin')
    permission_list_sysadmin = [
        # ---- app: auth ---- model: group
        ['add_group', 'auth', 'group'],                    # Can add group
        ['change_group', 'auth', 'group'],                    # Can change group
        ['delete_group', 'auth', 'group'],                    # Can delete group
        # ---- app: auth ---- model: user
        ['add_user', 'auth', 'user'],                    # Can add user
        ['change_user', 'auth', 'user'],                    # Can change user
        ['delete_user', 'auth', 'user'],                    # Can delete user
        # ---- app: configuration ---- model: parameter
        ['add_parameter', 'configuration', 'parameter'],                    # Can add parameter
        ['change_parameter', 'configuration', 'parameter'],                    # Can change parameter
        ['delete_parameter', 'configuration', 'parameter'],                    # Can delete parameter
        # ---- app: configuration ---- model: path
        ['add_path', 'configuration', 'path'],                    # Can add path
        ['change_path', 'configuration', 'path'],                    # Can change path
        ['delete_path', 'configuration', 'path'],                    # Can delete path
        # ---- app: configuration ---- model: eventtype
        ['add_eventtype', 'configuration', 'eventtype'],                    # Can add eventtype
        ['change_eventtype', 'configuration', 'eventtype'],                    # Can change eventtype
        ['delete_eventtype', 'configuration', 'eventtype'],                    # Can delete eventtype
        # ---- app: profiles ---- model: profile
        ['add_profile', 'profiles', 'profile'],                    # Can add profile
        ['change_profile', 'profiles', 'profile'],                    # Can change profile
        ['delete_profile', 'profiles', 'profile'],                    # Can delete profile
        # ---- app: profiles ---- model: submissionagreement
        ['add_submissionagreement', 'profiles', 'submissionagreement'],         # Can add submissionagreement
        ['change_submissionagreement', 'profiles', 'submissionagreement'],      # Can change submissionagreement
        ['delete_submissionagreement', 'profiles', 'submissionagreement'],      # Can delete submissionagreement
        # ---- app: groups_manager ---- model: grouptype
        ['add_grouptype', 'groups_manager', 'grouptype'],                    # Can add grouptype
        ['change_grouptype', 'groups_manager', 'grouptype'],                    # Can change grouptype
        ['delete_grouptype', 'groups_manager', 'grouptype'],                    # Can delete grouptype
    ]

    for p in permission_list_sysadmin:
        p_obj = Permission.objects.get(
            codename=p[0], content_type__app_label=p[1],
            content_type__model=p[2],
        )
        role_sysadmin.permissions.add(p_obj)

    #####################################
    # Users
    user_superuser, created = User.objects.get_or_create(
        first_name='superuser', last_name='Lastname',
        username='superuser', email='superuser@essolutions.se',
    )
    if created:
        user_superuser.set_password('superuser')
        user_superuser.is_staff = True
        user_superuser.is_superuser = True
        user_superuser.save()
        default_org.add_member(user_superuser.essauth_member)

    user_user, created = User.objects.get_or_create(
        first_name='user', last_name='Lastname',
        username='user', email='user@essolutions.se'
    )
    if created:
        user_user.set_password('user')
        user_user.save()
        default_org.add_member(user_user.essauth_member, roles=[role_user])

    user_admin, created = User.objects.get_or_create(
        first_name='admin', last_name='Lastname',
        username='admin', email='admin@essolutions.se',
    )
    if created:
        user_admin.set_password('admin')
        user_admin.is_staff = True
        user_admin.save()
        default_org.add_member(user_admin.essauth_member, roles=[role_user, role_admin])

    user_sysadmin, created = User.objects.get_or_create(
        first_name='sysadmin', last_name='Lastname',
        username='sysadmin', email='sysadmin@essolutions.se',
    )
    if created:
        user_sysadmin.set_password('sysadmin')
        user_sysadmin.is_staff = True
        user_sysadmin.save()
        default_org.add_member(user_sysadmin.essauth_member, roles=[role_sysadmin])

    return 0


def installDefaultPaths():
    dct = {
        'path_mimetypes_definitionfile': '/ESSArch/config/mime.types',
        'path_definitions': '/ESSArch/etp/env',
        'path_gate_reception': '/ESSArch/data/gate/reception',
        'path_preingest_prepare': '/ESSArch/data/etp/prepare',
        'path_preingest_reception': '/ESSArch/data/etp/reception',
        'path_ingest_reception': '/ESSArch/data/eta/reception/eft',
        'path_ingest_unidentified': '/ESSArch/data/eta/uip',
        'ingest_workarea': '/ESSArch/data/eta/work',
    }

    for key in dct:
        print('-> %s: %s' % (key, dct[key]))
        Path.objects.get_or_create(entity=key, defaults={'value': dct[key]})

    return 0


if __name__ == '__main__':
    installDefaultConfiguration()
