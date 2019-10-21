from django.conf import settings
from django.test import SimpleTestCase
from django.test.utils import override_settings

from ESSArch_Core.config import checks
from ESSArch_Core.crypto import generate_key


class EncryptionKeyCheckTests(SimpleTestCase):
    @property
    def func(self):
        from ESSArch_Core.config.checks import encryption_key_check
        return encryption_key_check

    @override_settings()
    def test_missing_key(self):
        del settings.ENCRYPTION_KEY
        self.assertEqual(self.func(None), [checks.E001])

    @override_settings(
        ENCRYPTION_KEY='',
    )
    def test_empty_key(self):
        self.assertEqual(self.func(None), [checks.E001])

    @override_settings(
        ENCRYPTION_KEY='123abc',
    )
    def test_invalid_key(self):
        self.assertEqual(self.func(None), [checks.E002])

    @override_settings(
        ENCRYPTION_KEY=generate_key(),
    )
    def test_valid_key(self):
        self.assertEqual(self.func(None), [])
