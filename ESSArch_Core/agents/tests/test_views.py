from countries_plus.models import Country
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from languages_plus.models import Language
from rest_framework import status
from rest_framework.test import APIClient

from ESSArch_Core.agents.models import (
    Agent,
    AgentIdentifier,
    AgentIdentifierType,
    AgentName,
    AgentNameType,
    AgentNote,
    AgentNoteType,
    AgentPlace,
    AgentPlaceType,
    AgentRelation,
    AgentRelationType,
    AgentType,
    AuthorityType,
    MainAgentType,
    RefCode,
    SourcesOfAuthority,
)
from ESSArch_Core.auth.models import Group, GroupType

User = get_user_model()


def add_permission(user, codename):
    agent_ctype = ContentType.objects.get(app_label="agents", model="agent")
    perm = Permission.objects.get(content_type=agent_ctype, codename=codename)
    user.user_permissions.add(perm)


class ListAgentTests(TestCase):
    fixtures = ['countries_data', 'languages_data']

    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')

        cls.user = User.objects.create(username='user')
        cls.member = cls.user.essauth_member

        cls.group = Group.objects.create(name='organization', group_type=cls.org_group_type)
        cls.group.add_member(cls.member)

        cls.main_agent_type = MainAgentType.objects.create()
        cls.agent_type = AgentType.objects.create(main_type=cls.main_agent_type)

        cls.ref_code = RefCode.objects.create(
            country=Country.objects.get(iso='SE'),
            repository_code='repo',
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.url = reverse('agent-list')

    def create_agent(self):
        agent = Agent.objects.create(
            level_of_detail=Agent.MINIMAL,
            script=Agent.LATIN,
            language=Language.objects.get(iso_639_1='sv'),
            record_status=Agent.DRAFT,
            type=self.agent_type,
            ref_code=self.ref_code,
            create_date=timezone.now(),
        )
        self.group.add_object(agent)

        return agent

    def test_empty(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_one_agent(self):
        self.create_agent()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_multiple_agents(self):
        self.create_agent()
        self.create_agent()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class CreateAgentTests(TestCase):
    fixtures = ['countries_data', 'languages_data']

    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('agent-list')

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

        self.main_agent_type = MainAgentType.objects.create()
        self.agent_type = AgentType.objects.create(main_type=self.main_agent_type)

        self.authority_type = AuthorityType.objects.create(name='test')
        self.identifier_type = AgentIdentifierType.objects.create(name='test')
        self.name_type = AgentNameType.objects.create(name='test')
        self.note_type = AgentNoteType.objects.create(name='test')
        self.place_type = AgentPlaceType.objects.create(name='test')
        self.relation_type = AgentRelationType.objects.create(name='test')

        self.ref_code = RefCode.objects.create(
            country=Country.objects.get(iso='SE'),
            repository_code='repo',
        )

    def create_agent(self):
        return Agent.objects.create(
            level_of_detail=Agent.MINIMAL,
            script=Agent.LATIN,
            language=Language.objects.get(iso_639_1='sv'),
            record_status=Agent.DRAFT,
            type=self.agent_type,
            ref_code=self.ref_code,
            create_date=timezone.now(),
        )

    def test_create_without_permission(self):
        response = self.client.post(
            self.url,
            data={
                'level_of_detail': Agent.MINIMAL,
                'script': Agent.LATIN,
                'language': 'sv',
                'record_status': Agent.DRAFT,
                'type': self.agent_type.pk,
                'ref_code': self.ref_code.pk,
                'names': [{
                    'main': 'test',
                    'type': self.name_type.pk,
                }],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_complete(self):
        add_permission(self.user, 'add_agent')
        related_agent = self.create_agent()

        response = self.client.post(
            self.url,
            data={
                'level_of_detail': Agent.MINIMAL,
                'script': Agent.LATIN,
                'language': 'sv',
                'record_status': Agent.DRAFT,
                'type': self.agent_type.pk,
                'ref_code': self.ref_code.pk,
                'identifiers': [{
                    'identifier': 'test',
                    'type': self.identifier_type.pk,
                }],
                'mandates': [{
                    'name': 'test',
                    'type': self.authority_type.pk,
                }],
                'names': [{
                    'main': 'test',
                    'type': self.name_type.pk,
                }],
                'notes': [{
                    'text': 'test',
                    'type': self.note_type.pk,
                }],
                'places': [{
                    'type': self.place_type.pk,
                    'topography': {
                        'name': 'test',
                        'type': 'test',
                        'reference_code': 'test',
                    },
                }],
                'related_agents': [{
                    'agent': related_agent.pk,
                    'type': self.relation_type.pk,
                }],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(reverse('agent-detail', args=(response.data['id'],)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_start_date_after_end_date(self):
        add_permission(self.user, 'add_agent')
        response = self.client.post(
            self.url,
            data={
                'level_of_detail': Agent.MINIMAL,
                'script': Agent.LATIN,
                'language': 'sv',
                'record_status': Agent.DRAFT,
                'type': self.agent_type.pk,
                'ref_code': self.ref_code.pk,
                'names': [{
                    'main': 'test',
                    'type': self.name_type.pk,
                }],
                'start_date': '1994-01-01',
                'end_date': '1984-01-01',
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_start_date_without_end_date(self):
        add_permission(self.user, 'add_agent')
        response = self.client.post(
            self.url,
            data={
                'level_of_detail': Agent.MINIMAL,
                'script': Agent.LATIN,
                'language': 'sv',
                'record_status': Agent.DRAFT,
                'type': self.agent_type.pk,
                'ref_code': self.ref_code.pk,
                'names': [{
                    'main': 'test',
                    'type': self.name_type.pk,
                }],
                'start_date': '1994-01-01',
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_name_start_date_after_name_end_date(self):
        add_permission(self.user, 'add_agent')
        response = self.client.post(
            self.url,
            data={
                'level_of_detail': Agent.MINIMAL,
                'script': Agent.LATIN,
                'language': 'sv',
                'record_status': Agent.DRAFT,
                'type': self.agent_type.pk,
                'ref_code': self.ref_code.pk,
                'names': [{
                    'main': 'test',
                    'type': self.name_type.pk,
                    'start_date': '1994-01-01',
                    'end_date': '1984-01-01',
                }],
                'notes': [{
                    'text': 'test',
                    'type': self.note_type.pk,
                }],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_name_start_date_without_name_end_date(self):
        add_permission(self.user, 'add_agent')
        response = self.client.post(
            self.url,
            data={
                'level_of_detail': Agent.MINIMAL,
                'script': Agent.LATIN,
                'language': 'sv',
                'record_status': Agent.DRAFT,
                'type': self.agent_type.pk,
                'ref_code': self.ref_code.pk,
                'names': [{
                    'main': 'test',
                    'type': self.name_type.pk,
                    'start_date': '1994-01-01',
                }],
                'notes': [{
                    'text': 'test',
                    'type': self.note_type.pk,
                }],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_without_names(self):
        add_permission(self.user, 'add_agent')
        response = self.client.post(
            self.url,
            data={
                'level_of_detail': Agent.MINIMAL,
                'script': Agent.LATIN,
                'language': 'sv',
                'record_status': Agent.DRAFT,
                'type': self.agent_type.pk,
                'ref_code': self.ref_code.pk,
                'names': [],
                'notes': [{
                    'text': 'test',
                    'type': self.note_type.pk,
                }],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UpdateAgentTests(TestCase):
    fixtures = ['countries_data', 'languages_data']

    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')

        cls.main_agent_type = MainAgentType.objects.create()
        cls.agent_type = AgentType.objects.create(main_type=cls.main_agent_type)

        cls.authority_type = AuthorityType.objects.create(name='test')
        cls.identifier_type = AgentIdentifierType.objects.create(name='test')
        cls.name_type = AgentNameType.objects.create(name='test')
        cls.note_type = AgentNoteType.objects.create(name='test')
        cls.place_type = AgentPlaceType.objects.create(name='test')
        cls.relation_type = AgentRelationType.objects.create(name='test')

        cls.ref_code = RefCode.objects.create(
            country=Country.objects.get(iso='SE'),
            repository_code='repo',
        )

    def setUp(self):
        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def create_agent(self):
        agent = Agent.objects.create(
            level_of_detail=Agent.MINIMAL,
            script=Agent.LATIN,
            language=Language.objects.get(iso_639_1='sv'),
            record_status=Agent.DRAFT,
            type=self.agent_type,
            ref_code=self.ref_code,
            create_date=timezone.now(),
        )
        self.group.add_object(agent)

        return agent

    def test_update_without_permission(self):
        agent = self.create_agent()
        url = reverse('agent-detail', args=[agent.pk])

        response = self.client.patch(
            url,
            data={
                'level_of_detail': Agent.PARTIAL,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_names(self):
        add_permission(self.user, 'change_agent')

        agent = self.create_agent()
        url = reverse('agent-detail', args=[agent.pk])

        # adding a name
        response = self.client.patch(
            url,
            data={
                'names': [{
                    'main': 'test',
                    'type': self.name_type.pk,
                }],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AgentName.objects.count(), 1)
        self.assertTrue(AgentName.objects.filter(agent=agent, main='test').exists())

        # adding another name
        response = self.client.patch(
            url,
            data={
                'names': [
                    {
                        'main': 'test',
                        'type': self.name_type.pk,
                    },
                    {
                        'main': 'test2',
                        'type': self.name_type.pk,
                    },
                ],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AgentName.objects.count(), 2)
        self.assertTrue(AgentName.objects.filter(agent=agent, main='test').exists())
        self.assertTrue(AgentName.objects.filter(agent=agent, main='test2').exists())

        # deleting a name
        response = self.client.patch(
            url,
            data={
                'names': [
                    {
                        'main': 'test2',
                        'type': self.name_type.pk,
                    },
                ],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AgentName.objects.count(), 1)
        self.assertTrue(AgentName.objects.filter(agent=agent, main='test2').exists())

        # should not be able to delete all names
        response = self.client.patch(
            url,
            data={
                'names': [],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(AgentName.objects.count(), 1)
        self.assertTrue(AgentName.objects.filter(agent=agent, main='test2').exists())

    def test_update_notes(self):
        add_permission(self.user, 'change_agent')

        agent = self.create_agent()
        url = reverse('agent-detail', args=[agent.pk])

        with self.subTest('basic'):
            response = self.client.patch(
                url,
                data={
                    'notes': [{
                        'text': 'test',
                        'type': self.note_type.pk,
                    }],
                }
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(AgentNote.objects.count(), 1)
            self.assertTrue(AgentNote.objects.filter(agent=agent, text='test').exists())

        with self.subTest('with create date'):
            create_date = timezone.now().isoformat()
            response = self.client.patch(
                url,
                data={
                    'notes': [{
                        'text': 'test',
                        'type': self.note_type.pk,
                        'create_date': create_date,
                    }],
                }
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(AgentNote.objects.count(), 1)
            self.assertTrue(AgentNote.objects.filter(agent=agent, text='test', create_date=create_date).exists())

    def test_update_identifiers(self):
        add_permission(self.user, 'change_agent')

        agent = self.create_agent()
        url = reverse('agent-detail', args=[agent.pk])

        response = self.client.patch(
            url,
            data={
                'identifiers': [{
                    'identifier': 'test',
                    'type': self.identifier_type.pk,
                }],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AgentIdentifier.objects.count(), 1)
        self.assertTrue(AgentIdentifier.objects.filter(agent=agent, identifier='test').exists())

    def test_update_mandates(self):
        add_permission(self.user, 'change_agent')

        agent = self.create_agent()
        url = reverse('agent-detail', args=[agent.pk])

        response = self.client.patch(
            url,
            data={
                'mandates': [{
                    'name': 'test',
                    'type': self.authority_type.pk,
                }],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(SourcesOfAuthority.objects.count(), 1)
        self.assertTrue(SourcesOfAuthority.objects.filter(agents=agent, name='test').exists())

    def test_update_places(self):
        add_permission(self.user, 'change_agent')

        agent = self.create_agent()
        url = reverse('agent-detail', args=[agent.pk])

        response = self.client.patch(
            url,
            data={
                'places': [{
                    'type': self.place_type.pk,
                    'topography': {
                        'name': 'test',
                        'type': 'test',
                        'reference_code': 'test',
                    },
                }],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AgentPlace.objects.count(), 1)
        self.assertTrue(AgentPlace.objects.filter(agent=agent, topography__name='test').exists())

    def test_update_related_agents(self):
        add_permission(self.user, 'change_agent')

        agent = self.create_agent()
        related_agent = self.create_agent()
        url = reverse('agent-detail', args=[agent.pk])

        response = self.client.patch(
            url,
            data={
                'related_agents': [{
                    'agent': related_agent.pk,
                    'type': self.relation_type.pk,
                }],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AgentRelation.objects.count(), 2)
        self.assertTrue(AgentRelation.objects.filter(agent_a=agent, agent_b=related_agent).exists())
        self.assertTrue(AgentRelation.objects.filter(agent_a=related_agent, agent_b=agent).exists())

    def test_add_relation_to_self(self):
        add_permission(self.user, 'change_agent')

        agent = self.create_agent()
        url = reverse('agent-detail', args=[agent.pk])

        response = self.client.patch(
            url,
            data={
                'related_agents': [{
                    'agent': agent.pk,
                    'type': self.relation_type.pk,
                }],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(AgentRelation.objects.exists())

    def test_add_same_relation_twice(self):
        add_permission(self.user, 'change_agent')

        agent = self.create_agent()
        url = reverse('agent-detail', args=[agent.pk])

        response = self.client.patch(
            url,
            data={
                'related_agents': [
                    {
                        'agent': agent.pk,
                        'type': self.relation_type.pk,
                    },
                    {
                        'agent': agent.pk,
                        'type': self.relation_type.pk,
                    }
                ],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(AgentRelation.objects.exists())


class DeleteAgentTests(TestCase):
    fixtures = ['countries_data', 'languages_data']

    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')

        cls.main_agent_type = MainAgentType.objects.create()
        cls.agent_type = AgentType.objects.create(main_type=cls.main_agent_type)

        cls.authority_type = AuthorityType.objects.create(name='test')
        cls.identifier_type = AgentIdentifierType.objects.create(name='test')
        cls.name_type = AgentNameType.objects.create(name='test')
        cls.note_type = AgentNoteType.objects.create(name='test')
        cls.place_type = AgentPlaceType.objects.create(name='test')
        cls.relation_type = AgentRelationType.objects.create(name='test')

        cls.ref_code = RefCode.objects.create(
            country=Country.objects.get(iso='SE'),
            repository_code='repo',
        )

    def setUp(self):
        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def create_agent(self):
        agent = Agent.objects.create(
            level_of_detail=Agent.MINIMAL,
            script=Agent.LATIN,
            language=Language.objects.get(iso_639_1='sv'),
            record_status=Agent.DRAFT,
            type=self.agent_type,
            ref_code=self.ref_code,
            create_date=timezone.now(),
        )
        self.group.add_object(agent)

        return agent

    def test_delete_without_permission(self):
        agent = self.create_agent()
        url = reverse('agent-detail', args=[agent.pk])

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_with_permission(self):
        add_permission(self.user, 'delete_agent')

        agent = self.create_agent()
        url = reverse('agent-detail', args=[agent.pk])

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
