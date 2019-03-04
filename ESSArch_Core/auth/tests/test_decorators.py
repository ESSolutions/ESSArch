from unittest.mock import call

from django.test import TestCase
from unittest import mock

from rest_framework import exceptions
from ESSArch_Core.auth.decorators import permission_required_or_403


class PermissionRequiredOr403Tests(TestCase):

    def setUp(self):
        self.mock_view = mock.Mock()
        self.mock_req = mock.Mock()
        self.args = (1, 2, 5)

    @staticmethod
    def dummy_decorated_view(view, request, *args, **kwargs):
        return "dummy_was_called", view, request, args, kwargs

    @mock.patch('ESSArch_Core.auth.decorators.get_object_or_404', return_value="dummy_obj")
    def test_when_user_has_the_right_perm(self, mock_get_obj_or_404):
        dummy_decorated_view = permission_required_or_403('p')(self.dummy_decorated_view)

        self.mock_view.get_queryset().model = "dummy_model"
        self.mock_req.user.has_perm.return_value = 'permission_1'
        kwargs = {"dummy_key_1": 1, "pk": 2, "dummy_key_3": 3}
        expected_calls = [call('p')]

        res_dummy, res_view, res_req, res_args, res_kwargs = dummy_decorated_view(
            self.mock_view, self.mock_req, *self.args, **kwargs)

        mock_get_obj_or_404.assert_called_once()
        self.assertEqual(self.mock_req.user.has_perm.mock_calls, expected_calls)

        self.assertEqual(res_dummy, "dummy_was_called")
        self.assertEqual(res_view, self.mock_view)
        self.assertEqual(res_req, self.mock_req)
        self.assertEqual(res_args, self.args)
        self.assertEqual(res_kwargs, kwargs)

    @mock.patch('ESSArch_Core.auth.decorators.get_object_or_404', return_value="dummy_obj")
    def test_when_user_has_the_right_perm_but_accept_global_perms_is_False(self, mock_get_obj_or_404):
        dummy_decorated_view = permission_required_or_403('p', accept_global_perms=False)(self.dummy_decorated_view)

        self.mock_view.get_queryset().model = "dummy_model"
        self.mock_req.user.has_perm.return_value = 'permission_1'
        kwargs = {"dummy_key_1": 1, "pk": 2, "dummy_key_3": 3}
        expected_calls = [call('p', 'dummy_obj')]

        res_dummy, res_view, res_req, res_args, res_kwargs = dummy_decorated_view(
            self.mock_view, self.mock_req, *self.args, **kwargs)

        mock_get_obj_or_404.assert_called_once()
        self.assertEqual(self.mock_req.user.has_perm.mock_calls, expected_calls)

        self.assertEqual(res_dummy, "dummy_was_called")
        self.assertEqual(res_view, self.mock_view)
        self.assertEqual(res_req, self.mock_req)
        self.assertEqual(res_args, self.args)
        self.assertEqual(res_kwargs, kwargs)

    @mock.patch('ESSArch_Core.auth.decorators.get_object_or_404', return_value="dummy_obj")
    def test_when_user_has_the_right_perm_for_obj(self, mock_get_obj_or_404):
        dummy_decorated_view = permission_required_or_403('p')(self.dummy_decorated_view)

        self.mock_view.get_queryset().model = "dummy_model"
        self.mock_req.user.has_perm.side_effect = [False, 'permission_1']
        kwargs = {"dummy_key_1": 1, "pk": 2, "dummy_key_3": 3}
        expected_calls = [call('p'), call('p', 'dummy_obj')]

        res_dummy, res_view, res_req, res_args, res_kwargs = dummy_decorated_view(
            self.mock_view, self.mock_req, *self.args, **kwargs)

        mock_get_obj_or_404.assert_called_once()
        self.assertEqual(self.mock_req.user.has_perm.mock_calls, expected_calls)

        self.assertEqual(res_dummy, "dummy_was_called")
        self.assertEqual(res_view, self.mock_view)
        self.assertEqual(res_req, self.mock_req)
        self.assertEqual(res_args, self.args)
        self.assertEqual(res_kwargs, kwargs)

    @mock.patch('ESSArch_Core.auth.decorators.get_object_or_404', return_value="dummy_obj")
    def test_when_list_of_perms_is_required(self, mock_get_obj_or_404):
        dummy_decorated_view = permission_required_or_403(['p1', 'p2'])(self.dummy_decorated_view)

        self.mock_view.get_queryset().model = "dummy_model"
        self.mock_req.user.has_perm.side_effect = [True, False, True, True]
        kwargs = {"dummy_key_1": 1, "pk": 2, "dummy_key_3": 3}
        expected_calls = [call('p1'), call('p2'), call('p1', 'dummy_obj'), call('p2', 'dummy_obj')]

        res_dummy, res_view, res_req, res_args, res_kwargs = dummy_decorated_view(
            self.mock_view, self.mock_req, *self.args, **kwargs)

        mock_get_obj_or_404.assert_called_once()
        self.assertEqual(self.mock_req.user.has_perm.mock_calls, expected_calls)

        self.assertEqual(res_dummy, "dummy_was_called")
        self.assertEqual(res_view, self.mock_view)
        self.assertEqual(res_req, self.mock_req)
        self.assertEqual(res_args, self.args)
        self.assertEqual(res_kwargs, kwargs)

    @mock.patch('ESSArch_Core.auth.decorators.get_object_or_404', return_value="dummy_obj")
    def test_when_user_does_not_have_permission_then_raise_exception(self, mock_get_obj_or_404):
        dummy_decorated_view = permission_required_or_403('p')(self.dummy_decorated_view)

        self.mock_view.get_queryset().model = "dummy_model"
        self.mock_req.user.has_perm.side_effect = [False, False]
        kwargs = {"dummy_key_1": 1, "pk": 2, "dummy_key_3": 3}
        expected_calls = [call('p'), call('p', 'dummy_obj')]

        with self.assertRaises(exceptions.PermissionDenied):
            dummy_decorated_view(self.mock_view, self.mock_req, *self.args, **kwargs)

        mock_get_obj_or_404.assert_called_once()
        self.assertEqual(self.mock_req.user.has_perm.mock_calls, expected_calls)

    @mock.patch('ESSArch_Core.auth.decorators.get_object_or_404', return_value="dummy_obj")
    def test_when_pk_does_not_exist_then_dont_try_to_get_the_object(self, mock_get_obj_or_404):
        dummy_decorated_view = permission_required_or_403('p')(self.dummy_decorated_view)

        self.mock_view.get_queryset().model = "dummy_model"
        self.mock_req.user.has_perm.side_effect = [False, 'permission_1']
        kwargs = {"dummy_key_1": 1, "dummy_key_3": 3}
        expected_calls = [call('p'), call('p', None)]

        res_dummy, res_view, res_req, res_args, res_kwargs = dummy_decorated_view(
            self.mock_view, self.mock_req, *self.args, **kwargs)

        mock_get_obj_or_404.assert_not_called()
        self.assertEqual(self.mock_req.user.has_perm.mock_calls, expected_calls)

        self.assertEqual(res_dummy, "dummy_was_called")
        self.assertEqual(res_view, self.mock_view)
        self.assertEqual(res_req, self.mock_req)
        self.assertEqual(res_args, self.args)
        self.assertEqual(res_kwargs, kwargs)

    @mock.patch('ESSArch_Core.auth.decorators.get_object_or_404', return_value="dummy_obj")
    def test_when_model_is_None_does_not_exist_then_dont_try_to_get_the_object(self, mock_get_obj_or_404):
        dummy_decorated_view = permission_required_or_403('p')(self.dummy_decorated_view)

        self.mock_view.get_queryset().model = None
        self.mock_req.user.has_perm.side_effect = [False, 'permission_1']
        kwargs = {"dummy_key_1": 1, "dummy_key_3": 3}
        expected_calls = [call('p'), call('p', None)]

        res_dummy, res_view, res_req, res_args, res_kwargs = dummy_decorated_view(
            self.mock_view, self.mock_req, *self.args, **kwargs)

        mock_get_obj_or_404.assert_not_called()
        self.assertEqual(self.mock_req.user.has_perm.mock_calls, expected_calls)

        self.assertEqual(res_dummy, "dummy_was_called")
        self.assertEqual(res_view, self.mock_view)
        self.assertEqual(res_req, self.mock_req)
        self.assertEqual(res_args, self.args)
        self.assertEqual(res_kwargs, kwargs)
