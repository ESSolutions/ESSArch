import time
from pydoc import locate
from unittest import SkipTest

from countries_plus.models import Country
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings, tag
from django.urls import reverse
from django.utils import timezone
from elasticsearch_dsl.connections import (
    connections,
    get_connection as get_es_connection,
)
from languages_plus.models import Language
from rest_framework import status
from rest_framework.test import APITestCase

from ESSArch_Core.agents.models import (
    Agent,
    AgentTagLink,
    AgentTagLinkRelationType,
    AgentType,
    MainAgentType,
    RefCode,
)
from ESSArch_Core.auth.models import Group, GroupType
from ESSArch_Core.configuration.models import Feature
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.search import alias_migration
from ESSArch_Core.tags.documents import Archive, Component, File
from ESSArch_Core.tags.models import (
    Structure,
    StructureType,
    Tag,
    TagStructure,
    TagVersion,
    TagVersionType,
)

User = get_user_model()


def get_test_client(nowait=False):
    client = get_es_connection('default')

    # wait for yellow status
    for _ in range(1 if nowait else 100):
        try:
            client.cluster.health(wait_for_status="yellow")
            return client
        except ConnectionError:
            time.sleep(0.1)
    else:
        # timeout
        raise SkipTest("Elasticsearch failed to start.")


@override_settings(ELASTICSEARCH_CONNECTIONS=settings.ELASTICSEARCH_TEST_CONNECTIONS)
@tag('requires-elasticsearch')
class ESSArchSearchBaseTestCase(APITestCase):
    @staticmethod
    def _get_client():
        return get_test_client()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connections.configure(**settings.ELASTICSEARCH_CONNECTIONS)
        cls.es_client = cls._get_client()

    def setUp(self):
        for _index_name, index_class in settings.ELASTICSEARCH_INDEXES['default'].items():
            doctype = locate(index_class)
            alias_migration.setup_index(doctype)

    def tearDown(self):
        self.es_client.indices.delete(index="*", ignore=404)
        self.es_client.indices.delete_template(name="*", ignore=404)


class ComponentSearchTestCase(ESSArchSearchBaseTestCase):
    fixtures = ['countries_data', 'languages_data']

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('search-list')
        Feature.objects.create(name='archival descriptions', enabled=True)
        cls.user = User.objects.create()
        permission = Permission.objects.get(codename='search')
        cls.user.user_permissions.add(permission)

        cls.component_type = TagVersionType.objects.create(name='component', archive_type=False)
        cls.archive_type = TagVersionType.objects.create(name='archive', archive_type=True)

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    @staticmethod
    def create_agent():
        return Agent.objects.create(
            type=AgentType.objects.create(main_type=MainAgentType.objects.create()),
            ref_code=RefCode.objects.create(
                country=Country.objects.get(iso='SE'),
                repository_code='repo',
            ),
            level_of_detail=0,
            record_status=0,
            script=0,
            language=Language.objects.get(iso_639_1='sv'),
            create_date=timezone.now(),
        )

    def test_search_component(self):
        component_tag = Tag.objects.create()
        component_tag_version = TagVersion.objects.create(
            tag=component_tag,
            type=self.component_type,
            elastic_index="component",
        )
        Component.from_obj(component_tag_version).save(refresh='true')

        with self.subTest('without archive'):
            res = self.client.get(self.url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(len(res.data['hits']), 1)

        structure_type = StructureType.objects.create()
        structure_template = Structure.objects.create(type=structure_type, is_template=True)

        archive_tag = Tag.objects.create()
        archive_tag_version = TagVersion.objects.create(
            tag=archive_tag,
            type=self.archive_type,
            elastic_index="archive",
        )
        structure, archive_tag_structure = structure_template.create_template_instance(archive_tag)
        Archive.from_obj(archive_tag_version).save(refresh='true')

        TagStructure.objects.create(tag=component_tag, parent=archive_tag_structure, structure=structure)
        Component.index_documents(remove_stale=True)

        with self.subTest('with archive'):
            res = self.client.get(self.url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(len(res.data['hits']), 1)
            self.assertEqual(res.data['hits'][0]['_id'], str(component_tag_version.pk))

    def test_filter_on_component_agent(self):
        agent = self.create_agent()

        component_tag = Tag.objects.create()
        component_tag_version = TagVersion.objects.create(
            tag=component_tag,
            type=self.component_type,
            elastic_index="component",
        )

        structure_type = StructureType.objects.create()
        structure_template = Structure.objects.create(type=structure_type, is_template=True)

        archive_tag = Tag.objects.create()
        archive_tag_version = TagVersion.objects.create(
            tag=archive_tag,
            type=self.archive_type,
            elastic_index="archive",
        )
        structure, archive_tag_structure = structure_template.create_template_instance(archive_tag)
        Archive.from_obj(archive_tag_version).save(refresh='true')

        TagStructure.objects.create(tag=component_tag, parent=archive_tag_structure, structure=structure)

        AgentTagLink.objects.create(
            agent=agent,
            tag=component_tag_version,
            type=AgentTagLinkRelationType.objects.create(),
        )
        Component.from_obj(component_tag_version).save(refresh='true')

        res = self.client.get(self.url, {'agents': str(agent.pk)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['hits']), 1)
        self.assertEqual(res.data['hits'][0]['_id'], str(component_tag_version.pk))

    def test_filter_on_archive_agent(self):
        agent = self.create_agent()

        component_tag = Tag.objects.create()
        component_tag_version = TagVersion.objects.create(
            tag=component_tag,
            type=self.component_type,
            elastic_index="component",
        )

        structure_type = StructureType.objects.create()
        structure_template = Structure.objects.create(type=structure_type, is_template=True)

        archive_tag = Tag.objects.create()
        archive_tag_version = TagVersion.objects.create(
            tag=archive_tag,
            type=self.archive_type,
            elastic_index="archive",
        )
        structure, archive_tag_structure = structure_template.create_template_instance(archive_tag)
        Archive.from_obj(archive_tag_version).save(refresh='true')

        TagStructure.objects.create(tag=component_tag, parent=archive_tag_structure, structure=structure)

        AgentTagLink.objects.create(
            agent=agent,
            tag=archive_tag_version,
            type=AgentTagLinkRelationType.objects.create(),
        )
        Component.from_obj(component_tag_version).save(refresh='true')

        res = self.client.get(self.url, {'agents': str(agent.pk)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['hits']), 1)
        self.assertEqual(res.data['hits'][0]['_id'], str(component_tag_version.pk))


class DocumentSearchTestCase(ESSArchSearchBaseTestCase):
    fixtures = ['countries_data', 'languages_data']

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('search-list')
        Feature.objects.create(name='archival descriptions', enabled=True)

        org_group_type = GroupType.objects.create(codename='organization')
        cls.group = Group.objects.create(group_type=org_group_type)
        cls.component_type = TagVersionType.objects.create(name='component', archive_type=False)
        cls.archive_type = TagVersionType.objects.create(name='archive', archive_type=True)

    def setUp(self):
        super().setUp()

        permission = Permission.objects.get(codename='search')
        self.user = User.objects.create()
        self.user.user_permissions.add(permission)
        self.group.add_member(self.user.essauth_member)

        self.client.force_authenticate(user=self.user)

    def test_search_document_in_ip_with_other_user_responsible_without_permission_to_see_it(self):
        other_user = User.objects.create(username='other')
        self.group.add_member(other_user.essauth_member)

        ip = InformationPackage.objects.create(responsible=other_user)
        self.group.add_object(ip)

        document_tag = Tag.objects.create(information_package=ip)
        document_tag_version = TagVersion.objects.create(
            tag=document_tag,
            type=self.component_type,
            elastic_index="document",
        )
        File.from_obj(document_tag_version).save(refresh='true')

        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['hits']), 0)

    def test_search_document_in_ip_with_other_user_responsible_with_permission_to_see_it(self):
        self.user.user_permissions.add(Permission.objects.get(codename='see_other_user_ip_files'))

        other_user = User.objects.create(username='other')
        self.group.add_member(other_user.essauth_member)

        ip = InformationPackage.objects.create(responsible=other_user)
        self.group.add_object(ip)

        document_tag = Tag.objects.create(information_package=ip)
        document_tag_version = TagVersion.objects.create(
            tag=document_tag,
            type=self.component_type,
            elastic_index="document",
        )
        File.from_obj(document_tag_version).save(refresh='true')

        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['hits']), 1)
        self.assertEqual(res.data['hits'][0]['_id'], str(document_tag_version.pk))
