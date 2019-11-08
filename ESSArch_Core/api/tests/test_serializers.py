from django.test import TestCase

from ESSArch_Core.api.serializers import DynamicModelSerializer
from ESSArch_Core.ip.models import InformationPackage


class InformationPackageSerializer(DynamicModelSerializer):
    class Meta:
        model = InformationPackage
        fields = ('label', 'object_identifier_value',)


class DynamicModelSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ip = InformationPackage.objects.create()

    def test_all_fields(self):
        data = InformationPackageSerializer(self.ip).data
        self.assertTrue('label' in data)
        self.assertTrue('object_identifier_value' in data)

    def test_selected_field(self):
        data = InformationPackageSerializer(self.ip, fields=['label']).data
        self.assertTrue('label' in data)
        self.assertFalse('object_identifier_value' in data)

    def test_omitted_field(self):
        data = InformationPackageSerializer(self.ip, omit=['label']).data
        self.assertFalse('label' in data)
        self.assertTrue('object_identifier_value' in data)
