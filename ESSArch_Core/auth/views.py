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
    LoginSerializer,
    OrganizationDetailSerializer,
    NotificationSerializer,
    NotificationReadSerializer,
    PermissionSerializer,
    UserSerializer,
    UserLoggedInSerializer,
    UserLoggedInWriteSerializer,
)

from ESSArch_Core.auth.models import Group, Notification

from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.shortcuts import reverse

from django_filters.rest_framework import DjangoFilterBackend

from rest_auth.views import (
    LoginView as rest_auth_LoginView,
    LogoutView as rest_auth_LogoutView,
)

from rest_framework import exceptions, permissions, status, viewsets
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

try:
    from djangosaml2.views import logout as saml2_logout
except ImportError:
    pass


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

class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.filter(group_type__codename='organization')

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
    filter_fields = ('seen',)

    def get_queryset(self):
        return self.request.user.notifications.all()

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return NotificationReadSerializer

        return NotificationSerializer

    def delete(self, request, *args, **kwargs):
        self.get_queryset().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoginView(rest_auth_LoginView):
    serializer_class = LoginSerializer

    def get_response(self):
        serializer = UserLoggedInSerializer(instance=self.user,
                                            context={'request': self.request})

        return Response(serializer.data)


class LogoutView(rest_auth_LogoutView):
    def post(self, request):
        if getattr(settings, 'ENABLE_ADFS_LOGIN', False):
            try:
                redirect_response = saml2_logout(request)
                new_location = redirect_response.get('Location')
                return Response({'redirect': new_location})
            except AttributeError:
                pass

        return super(LogoutView, self).post(request)
