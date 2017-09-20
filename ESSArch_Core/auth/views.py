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

from ESSArch_Core.auth.serializers import (
    GroupSerializer,
    GroupDetailSerializer,
    NotificationSerializer,
    NotificationReadSerializer,
    PermissionSerializer,
    UserSerializer,
    UserLoggedInSerializer,
)

from ESSArch_Core.auth.models import Notification

from django.conf import settings
from django.contrib.auth.models import User, Group, Permission
from django.shortcuts import reverse

from rest_auth.app_settings import LoginSerializer
from rest_auth.views import (
    LoginView as rest_auth_LoginView,
    LogoutView as rest_auth_LogoutView,
)

from rest_framework import exceptions, permissions, viewsets
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return GroupSerializer

        return GroupDetailSerializer


class MeView(RetrieveUpdateAPIView):
    serializer_class = UserLoggedInSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows permissions to be viewed or edited.
    """
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()

    def get_queryset(self):
        return self.request.user.notifications.all()

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return NotificationReadSerializer

        return NotificationSerializer


class LoginView(rest_auth_LoginView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        self.request = request
        try:
            self.serializer = self.get_serializer(data=self.request.data, context={'request': request})
            self.serializer.is_valid(raise_exception=True)
            self.login()
        except exceptions.ValidationError:
            raise exceptions.ParseError('Invalid username or password')

        return self.get_response()


class LogoutView(rest_auth_LogoutView):
    def post(self, request):
        if getattr(settings, 'ENABLE_ADFS_LOGIN', False):
            return Response({'redirect': reverse('saml2:saml2_logout')})

        return self.logout(request)
