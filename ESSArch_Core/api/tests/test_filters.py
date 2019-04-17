from django.test import TestCase
from django_filters import rest_framework as filters

from ESSArch_Core.api.filters import ListFilter
from ESSArch_Core.ip.models import InformationPackage


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
