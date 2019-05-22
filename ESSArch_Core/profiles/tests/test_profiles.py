"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Tools for Producer (ETP)
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from ESSArch_Core.ip.models import InformationPackage

from ESSArch_Core.profiles.models import SubmissionAgreement


class SaveSubmissionAgreement(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="admin")

        perm_list = [
            'create_new_sa_generation',
            'add_submissionagreement',
        ]
        perms = Permission.objects.filter(codename__in=perm_list)
        self.user.user_permissions.add(*perms)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.sa = SubmissionAgreement.objects.create()
        self.ip = InformationPackage.objects.create()

        self.url = reverse('submissionagreement-save', args=[self.sa.pk])

    def test_save_no_name(self):
        data = {
            'data': {'archivist_organization': 'new ao'},
            'information_package': str(self.ip.pk),
        }

        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SubmissionAgreement.objects.count(), 1)

    def test_save_empty_name(self):
        data = {
            'new_name': '',
            'data': {'archivist_organization': 'new ao'},
            'information_package': str(self.ip.pk),
        }

        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SubmissionAgreement.objects.count(), 1)

    def test_save_no_changes(self):
        self.sa.archivist_organization = 'initial'
        self.sa.save()

        data = {
            'new_name': 'new',
            'data': {'archivist_organization': 'initial'},
            'information_package': str(self.ip.pk),
        }

        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SubmissionAgreement.objects.count(), 1)

    def test_save_empty_required_value(self):
        self.sa.archivist_organization = ''
        self.sa.template = [
            {
                "key": "archivist_organization",
                "templateOptions": {
                    "required": True,
                },
            }
        ]
        self.sa.save()

        data = {
            'new_name': 'new',
            'data': {'archivist_organization': '', 'label': 'new_data'},
            'information_package': str(self.ip.pk),
        }

        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SubmissionAgreement.objects.count(), 1)

    def test_save_missing_required_value(self):
        self.sa.archivist_organization = ''
        self.sa.template = [
            {
                "key": "archivist_organization",
                "templateOptions": {
                    "required": True,
                },
            }
        ]
        self.sa.save()

        data = {
            'new_name': 'new',
            'data': {'label': 'new_data'},
            'information_package': str(self.ip.pk),
        }

        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SubmissionAgreement.objects.count(), 1)

    def test_save_changes(self):
        self.sa.archivist_organization = 'initial'
        self.sa.save()

        data = {
            'new_name': 'new',
            'data': {'archivist_organization': 'new ao'},
            'information_package': str(self.ip.pk),
        }

        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(SubmissionAgreement.objects.filter(name='', archivist_organization='initial').exists())
        self.assertTrue(SubmissionAgreement.objects.filter(name='new', archivist_organization='new ao').exists())

    def test_save_changes_without_permission(self):
        self.user.user_permissions.all().delete()
        self.sa.archivist_organization = 'initial'
        self.sa.save()

        data = {
            'new_name': 'new',
            'data': {'archivist_organization': 'new ao'},
            'information_package': str(self.ip.pk),
        }

        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
