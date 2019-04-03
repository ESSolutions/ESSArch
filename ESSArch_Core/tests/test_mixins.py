from django.test import TestCase
from rest_framework import serializers, status, viewsets
from rest_framework.test import APIRequestFactory

from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.mixins import GetObjectForUpdateViewMixin


class FooSerializer(serializers.ModelSerializer):
    class Meta:
        model = InformationPackage
        fields = ('pk',)


class SimpleViewSet(viewsets.ModelViewSet, GetObjectForUpdateViewMixin):
    queryset = InformationPackage.objects.all()
    permission_classes = ()
    serializer_class = FooSerializer

    def retrieve(self, request, pk=None):
        self.get_object_for_update()
        return super().retrieve(request, pk)


class ViewSetWithSelectRelated(SimpleViewSet):
    queryset = InformationPackage.objects.all().select_related('responsible')


class GetObjectForUpdateViewMixinTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.ip = InformationPackage.objects.create()

    def test_simple(self):
        request = self.factory.get('/rand')
        view = SimpleViewSet.as_view(actions={
            'get': 'retrieve',
        })
        response = view(request, pk=self.ip.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_with_select_related(self):
        request = self.factory.get('/rand')
        view = ViewSetWithSelectRelated.as_view(actions={
            'get': 'retrieve',
        })
        response = view(request, pk=self.ip.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
