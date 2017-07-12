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
from django.urls import reverse

from rest_framework import serializers

from ESSArch_Core.auth.models import UserProfile

from ESSArch_Core.serializers import DynamicHyperlinkedModelSerializer


class PermissionSerializer(DynamicHyperlinkedModelSerializer):
    content_type = serializers.PrimaryKeyRelatedField(queryset=ContentType.objects.all())

    class Meta:
        model = Permission
        fields = ('url', 'id', 'name', 'codename', 'group_set', 'content_type')


class GroupSerializer(DynamicHyperlinkedModelSerializer):
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
    class Meta:
        model = User
        fields = (
            'url', 'id', 'username', 'first_name', 'last_name', 'email',
            'last_login', 'date_joined',
        )
        read_only_fields = (
            'id', 'username', 'first_name', 'last_name', 'email', 'last_login',
            'date_joined', 'groups', 'is_staff', 'is_active', 'is_superuser',
        )


class UserLoggedInSerializer(UserSerializer):
    url = serializers.SerializerMethodField()
    permissions = serializers.ReadOnlyField(source='get_all_permissions')
    user_permissions = PermissionSerializer(many=True, read_only=True)
    groups = GroupSerializer(many=True, read_only=True)

    ip_list_columns = serializers.ListField(source='user_profile.ip_list_columns')
    ip_list_view_type = serializers.ChoiceField(
        choices=UserProfile.IP_LIST_VIEW_CHOICES, default=UserProfile.AIC, source='user_profile.ip_list_view_type'
    )

    def get_url(self, obj):
        return self.context['request'].build_absolute_uri(reverse('me'))

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('user_profile')

        user_profile = instance.user_profile

        user_profile.ip_list_columns = profile_data.get(
            'ip_list_columns',
            user_profile.ip_list_columns
        )
        user_profile.ip_list_view_type = profile_data.get(
            'ip_list_view_type',
            user_profile.ip_list_view_type
         )

        user_profile.save()

        return instance

    class Meta:
        model = User
        fields = (
            'url', 'id', 'username', 'first_name', 'last_name', 'email',
            'groups', 'is_staff', 'is_active', 'is_superuser', 'last_login',
            'date_joined', 'permissions', 'user_permissions',
            'ip_list_columns', 'ip_list_view_type',
        )
        read_only_fields = (
            'id', 'username', 'last_login', 'date_joined', 'groups',
            'is_staff', 'is_active', 'is_superuser',
        )
