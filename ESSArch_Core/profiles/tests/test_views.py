from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory

from ESSArch_Core.profiles.models import Profile, SubmissionAgreement
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
