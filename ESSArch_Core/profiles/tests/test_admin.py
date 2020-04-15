from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ESSArch_Core.configuration.models import Path, StoragePolicy
from ESSArch_Core.profiles.models import SubmissionAgreement


class SubmissionAgreementAdminTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(is_staff=True, is_superuser=True)

    def setUp(self):
        self.client.force_login(self.user)

    def test_add_view(self):
        response = self.client.get(reverse('admin:profiles_submissionagreement_add'))
        self.assertEqual(response.status_code, 200)

    def test_changelist_view(self):
        response = self.client.get(reverse('admin:profiles_submissionagreement_changelist'))
        self.assertEqual(response.status_code, 200)

    def test_change_view(self):
        policy = StoragePolicy.objects.create(
            ingest_path=Path.objects.create(entity='ingest'),
        )
        sa = SubmissionAgreement.objects.create(policy=policy)
        response = self.client.get(reverse('admin:profiles_submissionagreement_change', args=(str(sa.pk),)))
        self.assertEqual(response.status_code, 200)
