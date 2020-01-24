import time
from pydoc import locate
from unittest import SkipTest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse
from elasticsearch.helpers.test import ElasticsearchTestCase
from elasticsearch_dsl.connections import (
    connections,
    get_connection as get_es_connection,
)
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

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


@override_settings(
    ELASTICSEARCH_CONNECTIONS={
        'default': {
            'hosts': [
                {
                    'host': 'localhost',
                    'port': 19200,
                },
            ],
            'timeout': 60,
            'max_retries': 1,
        }
    }
)
class ESSArchSearchBaseTestCase(APITestCase):
    @staticmethod
    def _get_client():
        return get_test_client()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connections.configure(**settings.ELASTICSEARCH_CONNECTIONS)
        cls.es_client = cls._get_client()

        for _index_name, index_class in settings.ELASTICSEARCH_INDEXES['default'].items():
            doctype = locate(index_class)
            alias_migration.setup_index(doctype)

    def setUp(self):
        for _index_name, index_class in settings.ELASTICSEARCH_INDEXES['default'].items():
            doctype = locate(index_class)
            alias_migration.migrate(doctype, move_data=False, delete_old_index=True)

    def tearDown(self):
        self.es_client.indices.delete(index="*", ignore=404)
        self.es_client.indices.delete_template(name="*", ignore=404)


class ComponentSearchTestCase(ESSArchSearchBaseTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(is_superuser=True)
        permission = Permission.objects.get(codename='search')
        cls.user.user_permissions.add(permission)

        cls.component_type = TagVersionType.objects.create(name='component', archive_type=False)
        cls.archive_type = TagVersionType.objects.create(name='archive', archive_type=True)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.url = reverse('search-list')

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
            self.assertNotEqual(res.data['hits'], [])

        return
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
            print(res.data['hits'])
            self.assertEqual(len(res.data['hits']), 1)
            self.assertEqual(res.data['hits'][0]['_id'], str(component_tag_version.pk))
