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

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Permission, ContentType
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from rest_framework import exceptions, serializers

from ESSArch_Core.auth.models import Group, Notification, UserProfile
from ESSArch_Core.auth.util import get_organization_groups


User = get_user_model()


class PermissionSerializer(serializers.ModelSerializer):
    content_type = serializers.PrimaryKeyRelatedField(queryset=ContentType.objects.all())

    class Meta:
        model = Permission
        fields = ('id', 'name', 'codename', 'group_set', 'content_type')


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name', 'group_type',)


class GroupDetailSerializer(GroupSerializer):
    group_members = serializers.SerializerMethodField()

    def get_group_members(self, obj):
        users = User.objects.filter(essauth_member__essauth_groups=obj)
        return users.values_list('id', flat=True)

    class Meta(GroupSerializer.Meta):
        fields = GroupSerializer.Meta.fields + ('group_members',)


class OrganizationDetailSerializer(GroupSerializer):
    group_members = serializers.SerializerMethodField()

    def get_group_members(self, obj):
        users = User.objects.filter(essauth_member__in=obj.get_members(subgroups=True))
        return UserSerializer(users, many=True).data

    class Meta(GroupSerializer.Meta):
        fields = GroupSerializer.Meta.fields + ('group_members',)


class ChangeOrganizationSerializer(serializers.Serializer):
    organization = serializers.IntegerField()

    def validate_organization(self, org_id):
        user = self.context.get('request').user
        try:
            return get_organization_groups(user).get(pk=org_id)
        except Group.DoesNotExist:
            raise serializers.ValidationError('Invalid id')


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email',
            'last_login', 'date_joined',
        )
        read_only_fields = (
            'id', 'username', 'first_name', 'last_name', 'email', 'last_login',
            'date_joined', 'groups', 'is_staff', 'is_active', 'is_superuser',
        )


class UserFilteredOrganizationField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        request = self.context.get('request', None)
        if not request:
            return None
        return get_organization_groups(request.user)


class UserLoggedInSerializer(UserSerializer):
    url = serializers.SerializerMethodField()
    user_permissions = PermissionSerializer(many=True, read_only=True)
    permissions = serializers.SerializerMethodField()
    organizations = serializers.SerializerMethodField()

    current_organization = GroupSerializer(source='user_profile.current_organization')
    ip_list_columns = serializers.ListField(source='user_profile.ip_list_columns')
    ip_list_view_type = serializers.ChoiceField(
        choices=UserProfile.IP_LIST_VIEW_CHOICES, default=UserProfile.AIC, source='user_profile.ip_list_view_type'
    )
    notifications_enabled = serializers.BooleanField(source='user_profile.notifications_enabled')
    language = serializers.CharField(source='user_profile.language')

    def get_url(self, obj):
        return self.context['request'].build_absolute_uri(reverse('me'))

    def get_permissions(self, obj):
        return obj.get_all_permissions()

    def get_organizations(self, user):
        groups = get_organization_groups(user).order_by('name')
        serializer = GroupSerializer(data=groups, many=True)
        serializer.is_valid()
        return serializer.data

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('user_profile', {})

        user_profile = instance.user_profile

        user_profile.language = profile_data.get(
            'language',
            user_profile.language,
        )

        user_profile.current_organization = profile_data.get(
            'current_organization',
            user_profile.current_organization,
        )

        user_profile.ip_list_columns = profile_data.get(
            'ip_list_columns',
            user_profile.ip_list_columns
        )
        user_profile.ip_list_view_type = profile_data.get(
            'ip_list_view_type',
            user_profile.ip_list_view_type
        )

        user_profile.notifications_enabled = profile_data.get(
            'notifications_enabled',
            user_profile.notifications_enabled,
        )

        user_profile.save()

        return super().update(instance, validated_data)

    class Meta:
        model = User
        fields = (
            'url', 'id', 'username', 'first_name', 'last_name', 'email',
            'organizations', 'is_staff', 'is_active', 'is_superuser', 'last_login',
            'date_joined', 'permissions', 'user_permissions',
            'ip_list_columns', 'ip_list_view_type', 'current_organization',
            'notifications_enabled', 'language',
        )
        read_only_fields = (
            'id', 'username', 'last_login', 'date_joined', 'organizations',
            'is_staff', 'is_active', 'is_superuser',
        )


class UserLoggedInWriteSerializer(UserLoggedInSerializer):
    current_organization = UserFilteredOrganizationField(source='user_profile.current_organization')

    class Meta:
        model = User
        fields = UserLoggedInSerializer.Meta.fields
        read_only_fields = UserLoggedInSerializer.Meta.read_only_fields


class NotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True, default=serializers.CurrentUserDefault())

    def create(self, validated_data):
        if 'user' not in validated_data:
            validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    class Meta:
        model = Notification
        fields = (
            'id', 'user', 'level', 'message', 'time_created', 'seen'
        )


class NotificationReadSerializer(NotificationSerializer):
    level = serializers.SerializerMethodField()

    def get_level(self, obj):
        return obj.get_level_display()

    class Meta:
        model = NotificationSerializer.Meta.model
        fields = NotificationSerializer.Meta.fields


# Import from rest_auth.app_settings must be after UserLoggedInSerializer
from rest_auth.app_settings import LoginSerializer as rest_auth_LoginSerializer  # noqa isort:skip


class LoginSerializer(rest_auth_LoginSerializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, attrs):
        self.request = self.context.get('request')
        username = attrs.get('username')
        password = attrs.get('password')

        user = authenticate(username=username, password=password, request=self.request)

        # Did we get back an active user?
        if user:
            if not user.is_active:
                msg = _('User account is disabled')
                raise exceptions.ValidationError(msg)
        else:
            msg = _('Invalid username or password')
            raise exceptions.ValidationError(msg)

        # If required, is the email verified?
        if 'rest_auth.registration' in settings.INSTALLED_APPS:
            from allauth.account import app_settings
            if app_settings.EMAIL_VERIFICATION == app_settings.EmailVerificationMethod.MANDATORY:
                email_address = user.emailaddress_set.get(email=user.email)
                if not email_address.verified:
                    raise serializers.ValidationError(_('E-mail is not verified.'))

        attrs['user'] = user
        return attrs
