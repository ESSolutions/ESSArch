from django.contrib.auth import get_user_model
from django.test import TestCase
from django_filters import rest_framework as filters
from rest_framework import generics, serializers
from rest_framework.test import APIRequestFactory, force_authenticate

from ESSArch_Core.api.filters import ListFilter, SearchFilter
from ESSArch_Core.ip.models import InformationPackage

User = get_user_model()
factory = APIRequestFactory()


class ListFilterTests(TestCase):
    def test_filtering(self):
        InformationPackage.objects.create(state="Prepared")
        InformationPackage.objects.create(state="Created")
        InformationPackage.objects.create(state="Preserved")

        class F(filters.FilterSet):
            state = ListFilter()

            class Meta:
                model = InformationPackage
                fields = ['state']

        results = F(data={'state': 'Prepared'})
        self.assertEqual(len(results.qs), 1)

        results = F(data={'state': 'Prepared,Created'})
        self.assertEqual(len(results.qs), 2)


class SearchFilterTests(TestCase):
    def test_filtering(self):
        class SearchFilterSerializer(serializers.ModelSerializer):
            class Meta:
                model = InformationPackage
                fields = ('id',)

        class SearchListView(generics.ListAPIView):
            queryset = InformationPackage.objects.all()
            serializer_class = SearchFilterSerializer
            filter_backends = (SearchFilter,)
            search_fields = ('id',)

        ip = InformationPackage.objects.create()

        user = User.objects.create()
        view = SearchListView.as_view()
        request = factory.get('/', {'search': str(ip.pk)})
        force_authenticate(request, user=user)
        response = view(request)

        self.assertEqual(response.data, [
            {'id': str(ip.pk)},
        ])
