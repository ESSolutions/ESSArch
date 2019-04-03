from unittest import mock
from django.test import TestCase
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.decorators import action
from rest_framework import status, viewsets, serializers
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from ESSArch_Core.auth.permissions import ActionPermissions

User = get_user_model()


class MyModel(models.Model):
    class Meta:
        app_label = 'my_app'


class ActionPermissionsGetRequiredPermissionsTests(TestCase):

    def test_default_behavior(self):
        model_cls = MyModel()
        action_perm = ActionPermissions()

        self.assertEqual(action_perm.get_required_permissions('list', model_cls), [])
        self.assertEqual(action_perm.get_required_permissions('retrieve', model_cls), [])
        self.assertEqual(action_perm.get_required_permissions('create', model_cls), ['my_app.add_mymodel'])
        self.assertEqual(action_perm.get_required_permissions('update', model_cls), ['my_app.change_mymodel'])
        self.assertEqual(action_perm.get_required_permissions('partial_update', model_cls), ['my_app.change_mymodel'])
        self.assertEqual(action_perm.get_required_permissions('destroy', model_cls), ['my_app.delete_mymodel'])

        # Non existing
        non_existing_actions = ['run', 'get', 'GET', 'post', 'POST', 'put', 'PUT', 'delete', 'DELETE', 'head', 'HEAD']
        for method in non_existing_actions:
            self.assertEqual(action_perm.get_required_permissions(method, model_cls), [])


class TestViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'username'
        )


class TestView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = (ActionPermissions,)
    serializer_class = TestViewSerializer

    def list(self, request, *args, **kwargs):
        return Response(status=status.HTTP_200_OK, data="hello from list")

    def retrieve(self, request, *args, **kwargs):
        return Response(status=status.HTTP_200_OK, data="hello from retrieve")

    def create(self, request, *args, **kwargs):
        return Response(status=status.HTTP_201_CREATED, data="hello from create")

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_204_NO_CONTENT, data="hello from update")

    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_206_PARTIAL_CONTENT, data="hello from partial_update")

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_204_NO_CONTENT, data="hello from destroy")


class ActionPermissionsHasPermissionTests(TestCase):
    factory = APIRequestFactory()

    def setUp(self):
        self.user = User.objects.create()

    def get_response(self, method_name, action_name, user, authenticated=True):
        request = getattr(self.factory, method_name)('/')

        if authenticated:
            force_authenticate(request, user=user)

        return TestView.as_view({method_name: action_name})(request)

    def validate_get_list_and_get_retrieve(self, user):
        """
        Helper function so that we don't repeat our self.
        """

        # needs no permission
        response = self.get_response('get', 'list', user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, "hello from list")

        # needs no permission
        response = self.get_response('get', 'retrieve', user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, "hello from retrieve")

    @mock.patch('ESSArch_Core.auth.permissions.ActionPermissions.get_required_permissions')
    def test_no_permission(self, get_req_perms):
        get_req_perms.return_value = ["dummy_perm"]
        response = self.get_response('post', 'create', self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated(self):
        response = self.get_response('get', 'list', self.user, authenticated=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_with_only_add_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename='add_user'))

        # needs no permission
        self.validate_get_list_and_get_retrieve(self.user)

        # needs add permission
        response = self.get_response('post', 'create', self.user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, "hello from create")

        # needs change permission
        response = self.get_response('put', 'update', self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # needs change permission
        response = self.get_response('patch', 'partial_update', self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # needs delete permission
        response = self.get_response('delete', 'destroy', self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_with_only_change_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename='change_user'))

        # needs no permission
        self.validate_get_list_and_get_retrieve(self.user)

        # needs add permission
        response = self.get_response('post', 'create', self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # needs change permission
        response = self.get_response('put', 'update', self.user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, "hello from update")

        # needs change permission
        response = self.get_response('patch', 'partial_update', self.user)
        self.assertEqual(response.status_code, status.HTTP_206_PARTIAL_CONTENT)
        self.assertEqual(response.data, "hello from partial_update")

        # needs delete permission
        response = self.get_response('delete', 'destroy', self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_with_only_delete_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename='delete_user'))

        # needs no permission
        self.validate_get_list_and_get_retrieve(self.user)

        # needs add permission
        response = self.get_response('post', 'create', self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # needs change permission
        response = self.get_response('put', 'update', self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # needs change permission
        response = self.get_response('patch', 'partial_update', self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # needs delete permission
        response = self.get_response('delete', 'destroy', self.user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, "hello from destroy")

    def test_user_with_add_and_change_permissions(self):
        perm_list = [
            'add_user',
            'change_user',
        ]
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))

        # needs no permission
        self.validate_get_list_and_get_retrieve(self.user)

        # needs add permission
        response = self.get_response('post', 'create', self.user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, "hello from create")

        # needs change permission
        response = self.get_response('put', 'update', self.user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, "hello from update")

        # needs change permission
        response = self.get_response('patch', 'partial_update', self.user)
        self.assertEqual(response.status_code, status.HTTP_206_PARTIAL_CONTENT)
        self.assertEqual(response.data, "hello from partial_update")

        # needs delete permission
        response = self.get_response('delete', 'destroy', self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_with_add_and_delete_permissions(self):
        perm_list = [
            'add_user',
            'delete_user',
        ]
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))

        # needs no permission
        self.validate_get_list_and_get_retrieve(self.user)

        # needs add permission
        response = self.get_response('post', 'create', self.user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, "hello from create")

        # needs change permission
        response = self.get_response('put', 'update', self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # needs change permission
        response = self.get_response('patch', 'partial_update', self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # needs delete permission
        response = self.get_response('delete', 'destroy', self.user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, "hello from destroy")

    def test_user_with_change_and_delete_permissions(self):
        perm_list = [
            'change_user',
            'delete_user',
        ]
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))

        # needs no permission
        self.validate_get_list_and_get_retrieve(self.user)

        # needs add permission
        response = self.get_response('post', 'create', self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # needs change permission
        response = self.get_response('put', 'update', self.user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, "hello from update")

        # needs change permission
        response = self.get_response('patch', 'partial_update', self.user)
        self.assertEqual(response.status_code, status.HTTP_206_PARTIAL_CONTENT)
        self.assertEqual(response.data, "hello from partial_update")

        # needs delete permission
        response = self.get_response('delete', 'destroy', self.user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, "hello from destroy")

    def test_user_with_all_permissions(self):
        perm_list = [
            'add_user',
            'change_user',
            'delete_user',
        ]
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=perm_list))

        # needs no permission
        self.validate_get_list_and_get_retrieve(self.user)

        # needs add permission
        response = self.get_response('post', 'create', self.user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, "hello from create")

        # needs change permission
        response = self.get_response('put', 'update', self.user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, "hello from update")

        # needs change permission
        response = self.get_response('patch', 'partial_update', self.user)
        self.assertEqual(response.status_code, status.HTTP_206_PARTIAL_CONTENT)
        self.assertEqual(response.data, "hello from partial_update")

        # needs delete permission
        response = self.get_response('delete', 'destroy', self.user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, "hello from destroy")

    def test_when_model_permissions_are_ignored_and_user_has_no_permissions(self):
        class IgnoredModelPermissionView(TestView):
            _ignore_model_permissions = True

        def get_response(method_name, action_name, user, authenticated=True):
            request = getattr(self.factory, method_name)('/')

            if authenticated:
                force_authenticate(request, user=user)

            return IgnoredModelPermissionView.as_view({method_name: action_name})(request)

        # needs no permission
        self.validate_get_list_and_get_retrieve(self.user)

        # needs add permission
        response = get_response('post', 'create', self.user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, "hello from create")

        # needs change permission
        response = get_response('put', 'update', self.user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, "hello from update")

        # needs change permission
        response = get_response('patch', 'partial_update', self.user)
        self.assertEqual(response.status_code, status.HTTP_206_PARTIAL_CONTENT)
        self.assertEqual(response.data, "hello from partial_update")

        # needs delete permission
        response = get_response('delete', 'destroy', self.user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, "hello from destroy")

    def test_when_view_has_extra_function(self):
        class ExtraFunctionView(TestView):
            @action(detail=True, methods=['create'])
            def some_other(self, request, *args, **kwargs):
                return Response(status=status.HTTP_201_CREATED, data="hello from some_other_method")

        def get_response(method_name, action_name, user, authenticated=True):
            request = getattr(self.factory, method_name)('/')

            if authenticated:
                force_authenticate(request, user=user)

            return ExtraFunctionView.as_view({method_name: action_name})(request)

        # needs no permission
        self.validate_get_list_and_get_retrieve(self.user)

        # None default methods does not require any permissions per default
        response = get_response('post', 'some_other', self.user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, "hello from some_other_method")
