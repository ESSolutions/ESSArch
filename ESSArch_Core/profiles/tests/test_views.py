from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.profiles.models import (
    Profile,
    SubmissionAgreement,
    SubmissionAgreementIPData,
)
from ESSArch_Core.profiles.serializers import (
    ProfileSerializer,
    SubmissionAgreementSerializer,
)

User = get_user_model()


class GetAllProfilesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.url = reverse('profile-list')

        Profile.objects.create()

    def test_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        # get API response
        self.client.force_authenticate(user=self.user)
        request = APIRequestFactory().get(self.url)
        response = self.client.get(self.url)

        # get data from DB
        profiles = Profile.objects.all()
        serializer = ProfileSerializer(profiles, many=True, context={'request': request})

        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CreateProfileTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.url = reverse('profile-list')

    def test_unauthenticated(self):
        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_with_permission(self):
        perm = Permission.objects.get(codename='add_profile')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {'name': 'foo', 'profile_type': 'sip'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class GetAllSubmissionAgreementsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.url = reverse('submissionagreement-list')

        SubmissionAgreement.objects.create()

    def test_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        # get API response
        self.client.force_authenticate(user=self.user)
        request = APIRequestFactory().get(self.url)
        response = self.client.get(self.url)

        # get data from DB
        submission_agreements = SubmissionAgreement.objects.all()
        serializer = SubmissionAgreementSerializer(submission_agreements, many=True, context={'request': request})

        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CreateSubmissionAgreementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.url = reverse('submissionagreement-list')

    def test_unauthenticated(self):
        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {'name': 'foo'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_with_permission(self):
        perm = Permission.objects.get(codename='add_submissionagreement')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {'name': 'foo', 'label': 'Foo', 'type': 'sa', 'status': 'created'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class LockSubmissionAgreementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Path.objects.create(entity='temp', value='')

    def setUp(self):
        self.user = User.objects.create(username='user')

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def get_url(self, sa):
        return reverse('submissionagreement-lock', args=(str(sa.pk),))

    def test_without_permission(self):
        sa = SubmissionAgreement.objects.create()
        ip = InformationPackage.objects.create(submission_agreement=sa)

        res = self.client.post(self.get_url(sa), data={'ip': str(ip.pk)})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_with_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename='lock_sa'))

        sa = SubmissionAgreement.objects.create()
        ip = InformationPackage.objects.create(submission_agreement=sa)
        sa_ip_data = SubmissionAgreementIPData.objects.create(
            user=self.user,
            submission_agreement=sa,
            information_package=ip,
            data={'foo': 'bar'},
        )
        ip.submission_agreement_data = sa_ip_data
        ip.save()

        with self.subTest('valid data'):
            res = self.client.post(self.get_url(sa), data={'ip': str(ip.pk)})
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        ip.submission_agreement_locked = False
        ip.save()
        with self.subTest('invalid data'):
            with mock.patch('ESSArch_Core.profiles.views.SubmissionAgreementIPData.clean',
                            side_effect=ValidationError('invalid data')):
                res = self.client.post(self.get_url(sa), data={'ip': str(ip.pk)})
                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_as_responsible(self):
        sa = SubmissionAgreement.objects.create()
        ip = InformationPackage.objects.create(
            responsible=self.user,
            submission_agreement=sa,
        )

        res = self.client.post(self.get_url(sa), data={'ip': str(ip.pk)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class SubmissionAgreementIPDataViewSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Path.objects.create(entity='temp', value='')

        cls.sa = SubmissionAgreement.objects.create()

    def setUp(self):
        perms = Permission.objects.filter(codename__in=[
            'add_submissionagreementipdata',
            'change_submissionagreementipdata',
        ])
        self.user = User.objects.create(username='user')
        self.user.user_permissions.add(*perms)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def get_create_url(self):
        return reverse('submissionagreementipdata-list')

    def get_update_url(self, obj):
        return reverse('submissionagreementipdata-detail', args=(str(obj.pk),))

    def test_create(self):
        ip = InformationPackage.objects.create(submission_agreement=self.sa)
        res = self.client.post(self.get_create_url(), data={
            'information_package': str(ip.pk),
            'submission_agreement': str(self.sa.pk),
            'data': {'foo': 'bar'},
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_update(self):
        ip = InformationPackage.objects.create(submission_agreement=self.sa)
        sa_ip_data = SubmissionAgreementIPData.objects.create(
            submission_agreement=self.sa,
            information_package=ip,
            user=self.user,
        )

        rel_data = {'foo': 'bar'}
        res = self.client.patch(self.get_update_url(sa_ip_data), data={'data': rel_data})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        sa_ip_data.refresh_from_db()
        self.assertEqual(sa_ip_data.data, rel_data)

    def test_update_without_changes(self):
        ip = InformationPackage.objects.create(submission_agreement=self.sa)
        sa_ip_data = SubmissionAgreementIPData.objects.create(
            submission_agreement=self.sa,
            information_package=ip,
            user=self.user,
        )

        rel_data = {'foo': 'bar'}
        res = self.client.patch(self.get_update_url(sa_ip_data), data={'data': rel_data})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        sa_ip_data.refresh_from_db()
        self.assertEqual(sa_ip_data.data, rel_data)

    def test_update_locked_sa(self):
        ip = InformationPackage.objects.create(
            submission_agreement=self.sa,
            submission_agreement_locked=True,
        )
        sa_ip_data = SubmissionAgreementIPData.objects.create(
            submission_agreement=self.sa,
            information_package=ip,
            user=self.user,
        )

        rel_data = {'foo': 'bar'}
        res = self.client.patch(self.get_update_url(sa_ip_data), data={'data': rel_data})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        sa_ip_data.refresh_from_db()
        self.assertEqual(sa_ip_data.data, {})


class SubmissionAgreementTemplateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.url = reverse('profiles-submission-agreement-template')
        self.client.force_authenticate(user=self.user)

    def test_authenticated_with_permission(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
