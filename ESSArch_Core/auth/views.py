"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from django_filters.rest_framework import DjangoFilterBackend
from rest_auth.views import (
    LoginView as rest_auth_LoginView,
    LogoutView as rest_auth_LogoutView,
)
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ESSArch_Core.api.filters import SearchFilter
from ESSArch_Core.auth.models import Group, Notification
from ESSArch_Core.auth.serializers import (
    GroupDetailSerializer,
    GroupSerializer,
    LoginSerializer,
    NotificationReadSerializer,
    NotificationSerializer,
    OrganizationDetailSerializer,
    PermissionSerializer,
    UserLoggedInSerializer,
    UserLoggedInWriteSerializer,
    UserSerializer,
)
from ESSArch_Core.auth.util import users_in_organization

try:
    from djangosaml2.views import logout as saml2_logout
except ImportError:
    pass


User = get_user_model()
logger = logging.getLogger('essarch.auth')


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = (SearchFilter,)
    search_fields = ('username',)

    def get_queryset(self):
        user = self.request.user
        return users_in_organization(user).order_by('-date_joined')


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that lists groups
    """
    queryset = Group.objects.all()

    filter_backends = (SearchFilter,)
    search_fields = ('name',)

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Group.objects.all()

        return user.essauth_member.groups.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return GroupSerializer

        return GroupDetailSerializer


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that lists organizations
    """
    queryset = Group.objects.filter(group_type__codename='organization')

    filter_backends = (SearchFilter,)
    search_fields = ('name',)

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Group.objects.filter(group_type__codename='organization')

        return user.essauth_member.groups.filter(group_type__codename='organization')

    def get_serializer_class(self):
        if self.action == 'list':
            return GroupSerializer

        return OrganizationDetailSerializer


class MeView(RetrieveUpdateAPIView):
    serializer_class = UserLoggedInSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return UserLoggedInSerializer

        return UserLoggedInWriteSerializer


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows permissions to be viewed or edited.
    """
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('seen',)

    def get_queryset(self):
        return self.request.user.notifications.all()

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return NotificationReadSerializer

        return NotificationSerializer

    @action(detail=False, methods=['post'], url_path='set-all-seen')
    def set_all_seen(self, request):
        self.get_queryset().update(seen=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, *args, **kwargs):
        self.get_queryset().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([])
def login_services(req):
    services = []

    if getattr(settings, 'ENABLE_ADFS_LOGIN', False):
        services.append('adfs')

    return Response(services)


class LoginView(rest_auth_LoginView):
    serializer_class = LoginSerializer

    def get_response(self):
        serializer = UserLoggedInSerializer(instance=self.user,
                                            context={'request': self.request})

        return Response(serializer.data)


class LogoutView(rest_auth_LogoutView):
    def get(self, request, *args, **kwargs):
        if getattr(settings, 'ENABLE_ADFS_LOGIN', False):
            try:
                return saml2_logout(request)
            except Exception:
                logger.exception('Failed to logout using SAML, no active identity found')

        self.logout(request)
        next_page = resolve_url(settings.LOGOUT_REDIRECT_URL)
        return HttpResponseRedirect(next_page)
