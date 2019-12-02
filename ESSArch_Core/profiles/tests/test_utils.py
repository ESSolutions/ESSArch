from django.test import SimpleTestCase, TestCase

from ESSArch_Core.ip.models import Agent, InformationPackage
from ESSArch_Core.profiles.utils import LazyDict, fill_specification_data


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
