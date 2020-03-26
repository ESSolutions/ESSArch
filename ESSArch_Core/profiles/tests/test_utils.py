from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from ESSArch_Core.configuration.models import Path, StoragePolicy
from ESSArch_Core.ip.models import Agent, InformationPackage
from ESSArch_Core.profiles.models import Profile, SubmissionAgreement
from ESSArch_Core.profiles.utils import LazyDict, fill_specification_data
from ESSArch_Core.storage.models import StorageMethod

User = get_user_model()


class LazyDictTests(SimpleTestCase):
    def test_len(self):
        d = LazyDict({'a': 1, 'b': '2', 'c': False})
        self.assertEqual(len(d), 3)


class FillSpecificationDataTests(TestCase):
    def test_agents(self):
        ip = InformationPackage.objects.create()
        self.assertEqual(len(fill_specification_data(ip=ip)['AGENTS']), 0)

        agent = Agent.objects.create()
        ip.agents.add(agent)
        self.assertEqual(len(fill_specification_data(ip=ip)['AGENTS']), 1)

    def test_content_path(self):
        user = User.objects.create()
        ip = InformationPackage.objects.create(
            object_path="foo",
            package_type=InformationPackage.SIP,
        )
        self.assertEqual(fill_specification_data(ip=ip)['CONTENTPATH'], 'foo')

        sa = SubmissionAgreement.objects.create(
            profile_sip=Profile.objects.create(
                profile_type='sip',
                structure=[
                    {
                        'type': 'folder',
                        'name': 'data',
                        'use': 'content',
                    },
                ]
            ),
            policy=StoragePolicy.objects.create(
                cache_storage=StorageMethod.objects.create(),
                ingest_path=Path.objects.create(),
            ),
        )
        ip.submission_agreement = sa
        ip.save()
        sa.lock_to_information_package(ip, user)

        self.assertEqual(fill_specification_data(ip=ip)['CONTENTPATH'], 'foo/data')
