from countries_plus.models import Country
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
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

User = get_user_model()


class CreateAgentTests(TestCase):
    fixtures = ['countries_data', 'languages_data']

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('agent-list')

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

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

    def test_create(self):
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

    def test_create_start_date_after_end_date(self):
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

    def test_create_name_start_date_after_name_end_date(self):
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

    def test_create_without_names(self):
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

    def test_update_names(self):
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
        agent = self.create_agent()
        url = reverse('agent-detail', args=[agent.pk])

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

        # with create_date
        response = self.client.patch(
            url,
            data={
                'notes': [{
                    'text': 'test',
                    'type': self.note_type.pk,
                    'create_date': '2019-03-01 12:34:56',
                }],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AgentNote.objects.count(), 1)
        self.assertTrue(AgentNote.objects.filter(agent=agent, text='test', create_date='2019-03-01 12:34:56').exists())

    def test_update_identifiers(self):
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
        self.assertEqual(AgentRelation.objects.count(), 1)
        self.assertTrue(AgentRelation.objects.filter(agent_a=agent, agent_b=related_agent).exists())
