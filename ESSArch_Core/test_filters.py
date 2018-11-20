import datetime

from django.utils import timezone
from django.test import TestCase
from django_filters import rest_framework as filters

from ESSArch_Core.filters import IsoDateTimeFromToRangeFilter, ListFilter
from ESSArch_Core.ip.models import InformationPackage


class IsoDateTimeFromToRangeFilterTests(TestCase):
    def test_filtering(self):
        tz = timezone.get_current_timezone()
        InformationPackage.objects.create(
                entry_date=datetime.datetime(2016, 1, 1, 10, 0, tzinfo=tz))
        InformationPackage.objects.create(
                entry_date=datetime.datetime(2016, 1, 2, 12, 45, tzinfo=tz))
        InformationPackage.objects.create(
                entry_date=datetime.datetime(2016, 1, 3, 18, 15, tzinfo=tz))
        InformationPackage.objects.create(
                entry_date=datetime.datetime(2016, 1, 3, 19, 30, tzinfo=tz))

        class F(filters.FilterSet):
            entry_date = IsoDateTimeFromToRangeFilter()

            class Meta:
                model = InformationPackage
                fields = ['entry_date']

        results = F(data={
            'entry_date_after': '2016-01-02T10:00:00.000',
            'entry_date_before': '2016-01-03T19:00:00.000'
        })
        self.assertEqual(len(results.qs), 2)


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
