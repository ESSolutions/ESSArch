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
        self.assertIn('label', data)
        self.assertIn('object_identifier_value', data)

    def test_selected_field(self):
        data = InformationPackageSerializer(self.ip, fields=['label']).data
        self.assertIn('label', data)
        self.assertNotIn('object_identifier_value', data)

    def test_omitted_field(self):
        data = InformationPackageSerializer(self.ip, omit=['label']).data
        self.assertNotIn('label', data)
        self.assertIn('object_identifier_value', data)
