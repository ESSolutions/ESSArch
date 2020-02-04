from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework.views import APIView

from ESSArch_Core.configuration.decorators import feature_enabled_or_404
from ESSArch_Core.configuration.models import Feature


class FeatureEnabledOr404Tests(APITestCase):
    factory = APIRequestFactory()

    def test_non_existing_feature(self):
        class TestView(APIView):
            permission_classes = ()

            @feature_enabled_or_404('does not exist')
            def get(self, request):
                return Response()

        req = self.factory.get('/')
        resp = TestView.as_view()(req)

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_disabled_feature(self):
        class TestView(APIView):
            permission_classes = ()

            @feature_enabled_or_404('disabled')
            def get(self, request):
                return Response()

        Feature.objects.create(name='disabled', enabled=False)
        req = self.factory.get('/')
        resp = TestView.as_view()(req)

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_enabled_feature(self):
        class TestView(APIView):
            permission_classes = ()

            @feature_enabled_or_404('enabled')
            def get(self, request):
                return Response()

        Feature.objects.create(name='enabled', enabled=True)

        req = self.factory.get('/')
        resp = TestView.as_view()(req)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
