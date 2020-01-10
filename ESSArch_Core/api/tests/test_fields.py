import os

from rest_framework import serializers
from rest_framework.test import APITestCase

from ESSArch_Core.api.fields import FilePathField


class FilePathFieldTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.field = FilePathField(os.path.abspath(os.path.dirname(__file__)))

    def test_valid_path(self):
        self.assertEqual(self.field.run_validation(__file__), __file__)
        self.assertEqual(self.field.run_validation(os.path.basename(__file__)), os.path.basename(__file__))

    def test_invalid_path(self):
        with self.assertRaises(serializers.ValidationError):
            self.field.run_validation('invalid_file')
