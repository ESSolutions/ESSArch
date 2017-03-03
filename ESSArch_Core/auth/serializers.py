"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Core
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

from django.contrib.auth.models import User, Group, Permission, ContentType

from rest_framework import serializers


class PermissionSerializer(serializers.HyperlinkedModelSerializer):
    content_type = serializers.PrimaryKeyRelatedField(queryset=ContentType.objects.all())

    class Meta:
        model = Permission
        fields = ('url', 'id', 'name', 'codename', 'group_set', 'content_type')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    permissions = PermissionSerializer(many=True)

    class Meta:
        model = Group
        fields = ('url', 'id', 'name', 'permissions',)


class GroupDetailSerializer(GroupSerializer):
    class Meta:
        model = Group
        fields = GroupSerializer.Meta.fields + (
            'user_set',
        )


class UserSerializer(serializers.HyperlinkedModelSerializer):
    permissions = serializers.ReadOnlyField(source='get_all_permissions')
    user_permissions = PermissionSerializer(many=True)
    groups = GroupSerializer(many=True)

    class Meta:
        model = User
        fields = (
            'url', 'id', 'username', 'first_name', 'last_name', 'email',
            'groups', 'is_staff', 'is_active', 'is_superuser', 'last_login',
            'date_joined', 'permissions', 'user_permissions',
        )
        read_only_fields = (
            'last_login', 'date_joined',
        )
