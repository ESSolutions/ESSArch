"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

from django.test import TestCase

from ESSArch_Core.profiles.models import (
    Profile,
    ProfileSA,
    SubmissionAgreement,
)


class SubmissionAgreementTestCase(TestCase):
    def test_copy(self):
        sa = SubmissionAgreement.objects.create()
        profile = Profile.objects.create()
        ProfileSA.objects.create(submission_agreement=sa, profile=profile)

        name = 'new'
        data = {'archivist_organization': 'new ao'}

        new = sa.copy(data, name)

        self.assertNotEqual(new.pk, sa.pk)
        self.assertEqual(new.name, name)
        self.assertEqual(new.archivist_organization, data['archivist_organization'])
        self.assertTrue(ProfileSA.objects.filter(submission_agreement=new, profile=profile).exists())
