from ESSArch_Core.auth.decorators import permission_required_or_403
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

User = get_user_model()


class PermissionRequiredOr403Tests(TestCase):
    factory = APIRequestFactory()

    def test_no_permission(self):
        class TestView(APIView):
            @permission_required_or_403('ip.add_informationpackage')
            def get(self, request, format=None):
                return Response({})

        user = User.objects.create()
        request = self.factory.get('/')
        force_authenticate(request, user=user)
        response = TestView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_permission(self):
        class TestView(APIView):
            @permission_required_or_403('ip.add_informationpackage')
            def get(self, request, format=None):
                return Response({})

        user = User.objects.create()
        user.user_permissions.add(Permission.objects.get(codename='add_informationpackage'))
        request = self.factory.get('/')
        force_authenticate(request, user=user)
        response = TestView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_multiple_permissions_granted(self):
        class TestView(APIView):
            @permission_required_or_403(['ip.add_informationpackage', 'ip.delete_informationpackage'])
            def get(self, request, format=None):
                return Response({})

        user = User.objects.create()
        user.user_permissions.add(*Permission.objects.filter(
            codename__in=('add_informationpackage', 'delete_informationpackage')))
        request = self.factory.get('/')
        force_authenticate(request, user=user)
        response = TestView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_multiple_permissions_when_not_all_granted(self):
        class TestView(APIView):
            @permission_required_or_403([
                'ip.add_informationpackage',
                'ip.delete_informationpackage',
                'ip.change_informationpackage',
            ])
            def get(self, request, format=None):
                return Response({})

        user = User.objects.create()
        user.user_permissions.add(*Permission.objects.filter(
            codename__in=('add_informationpackage', 'delete_informationpackage')))
        request = self.factory.get('/')
        force_authenticate(request, user=user)
        response = TestView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_multiple_permissions_granted_none_global_perms(self):
        class TestView(APIView):
            @permission_required_or_403(
                ['ip.add_informationpackage', 'ip.delete_informationpackage'],
                accept_global_perms=False
            )
            def get(self, request, format=None):
                return Response({})

        user = User.objects.create()
        user.user_permissions.add(*Permission.objects.filter(
            codename__in=('add_informationpackage', 'delete_informationpackage')))
        request = self.factory.get('/')
        force_authenticate(request, user=user)
        response = TestView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
