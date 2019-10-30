from django.contrib.auth import get_user_model
from django.test import TestCase
from django_filters import rest_framework as filters
from rest_framework import generics, permissions, serializers
from rest_framework.test import APIRequestFactory, force_authenticate

from ESSArch_Core.api.filters import (
    CharSuffixRangeFilter,
    ListFilter,
    SearchFilter,
)
from ESSArch_Core.ip.models import InformationPackage

User = get_user_model()
factory = APIRequestFactory()


class CharSuffixRangeFilterTests(TestCase):
    class F(filters.FilterSet):
        label = CharSuffixRangeFilter()

        class Meta:
            model = InformationPackage
            fields = ['label']

    def setUp(self):
        InformationPackage.objects.create(label="AA0010")
        InformationPackage.objects.create(label="AA0020")
        InformationPackage.objects.create(label="AA0030")
        InformationPackage.objects.create(label="AA0040")
        InformationPackage.objects.create(label="AA0050")

        InformationPackage.objects.create(label="AA0A10")
        InformationPackage.objects.create(label="AA00BB")
        InformationPackage.objects.create(label="foo")

    def test_filtering(self):
        results = self.F(data={'label_min': 'AA0010', 'label_max': 'AA0050'})
        self.assertTrue(results.is_valid())
        self.assertEqual(len(results.qs), 5)

        results = self.F(data={'label_min': 'AA0020', 'label_max': 'AA0040'})
        self.assertEqual(len(results.qs), 3)

    def test_different_lengths(self):
        results = self.F(data={'label_min': 'AA0010', 'label_max': 'AA50'})
        self.assertFalse(results.is_valid())

    def test_different_formats(self):
        with self.subTest():
            results = self.F(data={'label_min': 'AA0010', 'label_max': 'AA0A50'})
            self.assertFalse(results.is_valid())

        with self.subTest():
            results = self.F(data={'label_min': 'AA0010', 'label_max': 'BB0050'})
            self.assertFalse(results.is_valid())


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
            permission_classes = (permissions.IsAuthenticated,)
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
