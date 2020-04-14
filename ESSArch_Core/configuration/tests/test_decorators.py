from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework.views import APIView

from ESSArch_Core.configuration.decorators import feature_enabled_or_404
from ESSArch_Core.configuration.models import Feature


class FeatureEnabledOr404Tests(APITestCase):
    factory = APIRequestFactory()

    @staticmethod
    def create_view(feature):
        @method_decorator(feature_enabled_or_404(feature), name='initial')
        class TestView(APIView):
            permission_classes = ()

            def get(self, request):
                return Response()

            def post(self, request):
                return Response()

        return TestView.as_view()

    def test_non_existing_feature(self):
        view = self.create_view('does not exist')

        req = self.factory.get('/')
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        req = self.factory.post('/')
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_disabled_feature(self):
        Feature.objects.create(name='disabled', enabled=False)
        view = self.create_view('enabled')

        req = self.factory.get('/')
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        req = self.factory.post('/')
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_enabled_feature(self):
        Feature.objects.create(name='enabled', enabled=True)
        view = self.create_view('enabled')

        req = self.factory.get('/')
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        req = self.factory.post('/')
        resp = view(req)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
