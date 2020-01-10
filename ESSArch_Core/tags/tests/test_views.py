from unittest import mock

from countries_plus.models import Country
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from languages_plus.models import Language
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from ESSArch_Core.agents.models import (
    Agent,
    AgentTagLink,
    AgentTagLinkRelationType,
    AgentType,
    MainAgentType,
    RefCode,
)
from ESSArch_Core.auth.models import Group, GroupType
from ESSArch_Core.configuration.models import EventType
from ESSArch_Core.tags.models import (
    Delivery,
    DeliveryType,
    Location,
    LocationFunctionType,
    LocationLevelType,
    NodeRelationType,
    Structure,
    StructureRelation,
    StructureRelationType,
    StructureType,
    StructureUnit,
    StructureUnitRelation,
    StructureUnitType,
    Tag,
    TagStructure,
    TagVersion,
    TagVersionType,
    Transfer,
)
from ESSArch_Core.tags.serializers import (
    NON_EDITABLE_STRUCTURE_CHANGE_ERROR,
    PUBLISHED_STRUCTURE_CHANGE_ERROR,
    STRUCTURE_INSTANCE_RELATION_ERROR,
)

User = get_user_model()


def refresh_user(user):
    return User.objects.get(pk=user.pk)


def create_structure(structure_type, template=True):
    return Structure.objects.create(type=structure_type, is_template=template)


def create_structure_unit(structure_unit_type, structure, ref_code):
    return StructureUnit.objects.create(
        structure=structure,
        type=structure_unit_type,
        reference_code=ref_code
    )


class ListStructureTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()
        cls.url = reverse('structure-list')
        cls.user = User.objects.create(username='user')

        cls.structure_type = StructureType.objects.create(name='test')

    def test_empty(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_one_structure(self):
        self.client.force_authenticate(user=self.user)
        create_structure(self.structure_type)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_multiple_structures(self):
        self.client.force_authenticate(user=self.user)
        create_structure(self.structure_type)
        create_structure(self.structure_type)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class CreateStructureTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('structure-list')

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.client.force_authenticate(user=self.user)

    def test_without_permission(self):
        response = self.client.post(self.url,)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create(self):
        perm = Permission.objects.get(codename='add_structure')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        structure_type = StructureType.objects.create(name='test')

        response = self.client.post(
            self.url,
            data={
                'name': 'foo',
                'type': structure_type.pk,
                'start_date': '2010-01-01 12:34:56',
                'end_date': '2020-01-01 12:34:56',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Structure.objects.count(), 1)
        self.assertTrue(Structure.objects.filter(name='foo', created_by=self.user, revised_by=self.user).exists())

    def test_create_start_date_after_end_date(self):
        perm = Permission.objects.get(codename='add_structure')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        structure_type = StructureType.objects.create(name='test')

        response = self.client.post(
            self.url,
            data={
                'name': 'foo',
                'type': structure_type.pk,
                'start_date': '2020-01-01 12:34:56',
                'end_date': '2010-01-01 12:34:56',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_related_template(self):
        perm = Permission.objects.get(codename='add_structure')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        structure_type = StructureType.objects.create(name='test')
        relation_type = StructureRelationType.objects.create(name="test")
        other_structure = create_structure(structure_type)

        response = self.client.post(
            self.url,
            data={
                'name': 'foo',
                'type': structure_type.pk,
                'related_structures': [
                    {
                        'structure': other_structure.pk,
                        'type': relation_type.pk,
                    }
                ],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Structure.objects.count(), 2)
        self.assertEqual(StructureRelation.objects.count(), 2)

        structure = Structure.objects.get(name='foo')

        self.assertTrue(
            StructureRelation.objects.filter(
                structure_a=structure, structure_b=other_structure, type=relation_type
            ).exists()
        )
        self.assertTrue(
            StructureRelation.objects.filter(
                structure_a=other_structure, structure_b=structure, type=relation_type
            ).exists()
        )

    def test_create_with_related_instance(self):
        perm = Permission.objects.get(codename='add_structure')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        structure_type = StructureType.objects.create(name='test')
        relation_type = StructureRelationType.objects.create(name="test")
        other_structure = create_structure(structure_type, template=False)

        response = self.client.post(
            self.url,
            data={
                'name': 'foo',
                'type': structure_type.pk,
                'related_structures': [
                    {
                        'structure': other_structure.pk,
                        'type': relation_type.pk,
                    }
                ],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Structure.objects.count(), 1)
        self.assertFalse(StructureRelation.objects.exists())


class UpdateStructureTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.client.force_authenticate(user=self.user)

        self.structure_type = StructureType.objects.create(name='test')

    def test_without_permission(self):
        structure = create_structure(self.structure_type)
        url = reverse('structure-detail', args=[structure.pk])

        response = self.client.patch(
            url,
            data={
                'name': 'bar',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update(self):
        structure = create_structure(self.structure_type)
        url = reverse('structure-detail', args=[structure.pk])

        perm = Permission.objects.get(codename='change_structure')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            url,
            data={
                'name': 'bar',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Structure.objects.count(), 1)
        self.assertTrue(Structure.objects.filter(name='bar', created_by=None, revised_by=self.user).exists())

    def test_update_published_structure(self):
        structure = create_structure(self.structure_type)
        structure.publish()
        url = reverse('structure-detail', args=[structure.pk])

        perm = Permission.objects.get(codename='change_structure')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            url,
            data={
                'name': 'bar',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'non_field_errors': [PUBLISHED_STRUCTURE_CHANGE_ERROR]})

    def test_update_unpublished_structure(self):
        structure = create_structure(self.structure_type)
        structure.publish()
        structure.unpublish()
        url = reverse('structure-detail', args=[structure.pk])

        perm = Permission.objects.get(codename='change_structure')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            url,
            data={
                'name': 'bar',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {
                'non_field_errors': [
                    NON_EDITABLE_STRUCTURE_CHANGE_ERROR.format(structure.name),
                ]
            }
        )

    def test_update_relations(self):
        perm = Permission.objects.get(codename='change_structure')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        structure = create_structure(self.structure_type)
        other_structure = create_structure(self.structure_type)
        relation_type = StructureRelationType.objects.create(name="test")
        url = reverse('structure-detail', args=[structure.pk])

        response = self.client.patch(
            url,
            data={
                'related_structures': [
                    {
                        'structure': other_structure.pk,
                        'type': relation_type.pk,
                    }
                ],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(StructureRelation.objects.count(), 2)

        self.assertTrue(
            StructureRelation.objects.filter(
                structure_a=structure, structure_b=other_structure, type=relation_type
            ).exists()
        )
        self.assertTrue(
            StructureRelation.objects.filter(
                structure_a=other_structure, structure_b=structure, type=relation_type
            ).exists()
        )

    def test_update_relations_published_structure(self):
        perm = Permission.objects.get(codename='change_structure')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        structure = create_structure(self.structure_type)
        structure.publish()
        other_structure = create_structure(self.structure_type)
        relation_type = StructureRelationType.objects.create(name="test")
        url = reverse('structure-detail', args=[structure.pk])

        response = self.client.patch(
            url,
            data={
                'related_structures': [
                    {
                        'structure': other_structure.pk,
                        'type': relation_type.pk,
                    }
                ],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(StructureRelation.objects.count(), 2)

        self.assertTrue(
            StructureRelation.objects.filter(
                structure_a=structure, structure_b=other_structure, type=relation_type
            ).exists()
        )
        self.assertTrue(
            StructureRelation.objects.filter(
                structure_a=other_structure, structure_b=structure, type=relation_type
            ).exists()
        )

    def test_update_relations_structure_from_instance(self):
        perm = Permission.objects.get(codename='change_structure')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        structure = create_structure(self.structure_type, template=False)
        other_structure = create_structure(self.structure_type)
        relation_type = StructureRelationType.objects.create(name="test")
        url = reverse('structure-detail', args=[structure.pk])

        response = self.client.patch(
            url,
            data={
                'related_structures': [
                    {
                        'structure': other_structure.pk,
                        'type': relation_type.pk,
                    }
                ],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'non_field_errors': [STRUCTURE_INSTANCE_RELATION_ERROR]})
        self.assertFalse(StructureRelation.objects.exists())

    def test_update_relations_structure_to_instance(self):
        perm = Permission.objects.get(codename='change_structure')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        structure = create_structure(self.structure_type)
        other_structure = create_structure(self.structure_type, template=False)
        relation_type = StructureRelationType.objects.create(name="test")
        url = reverse('structure-detail', args=[structure.pk])

        response = self.client.patch(
            url,
            data={
                'related_structures': [
                    {
                        'structure': other_structure.pk,
                        'type': relation_type.pk,
                    }
                ],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(StructureRelation.objects.exists())


class PublishStructureTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.client.force_authenticate(user=self.user)

        self.structure_type = StructureType.objects.create(name='test')

    def test_without_permission(self):
        structure = create_structure(self.structure_type)
        url = reverse('structure-publish', args=[structure.pk])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        structure.refresh_from_db()
        self.assertFalse(structure.published)
        self.assertIsNone(structure.published_date)

    def test_publish_template(self):
        structure = create_structure(self.structure_type)
        url = reverse('structure-publish', args=[structure.pk])

        perm = Permission.objects.get(codename='publish_structure')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        structure.refresh_from_db()
        self.assertTrue(structure.published)
        self.assertIsNotNone(structure.published_date)

    def test_publish_instance(self):
        structure = create_structure(self.structure_type, False)
        url = reverse('structure-publish', args=[structure.pk])

        perm = Permission.objects.get(codename='publish_structure')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        structure.refresh_from_db()
        self.assertFalse(structure.published)
        self.assertIsNone(structure.published_date)


class UnpublishStructureTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.client.force_authenticate(user=self.user)

        self.structure_type = StructureType.objects.create(name='test')
        self.structure = create_structure(self.structure_type, False)
        self.structure.published = True
        self.structure.save()

        self.url = reverse('structure-unpublish', args=[self.structure.pk])

    def test_without_permission(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.structure.refresh_from_db()
        self.assertTrue(self.structure.published)

    def test_unpublish_template(self):
        perm = Permission.objects.get(codename='unpublish_structure')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.structure.refresh_from_db()
        self.assertFalse(self.structure.published)


class ListStructureUnitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('structureunit-list')
        cls.user = User.objects.create(username='user', is_superuser=True)

        cls.structure_type = StructureType.objects.create(name='test')
        cls.unit_type = StructureUnitType.objects.create(name="test", structure_type=cls.structure_type)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @mock.patch('ESSArch_Core.tags.signals.TagVersion.get_doc')
    def test_leaf_unit(self, mock_doc):
        structure = create_structure(self.structure_type)

        a = create_structure_unit(self.unit_type, structure, 'a')
        a1 = create_structure_unit(self.unit_type, structure, 'a1')
        a1.parent = a
        a1.save()

        b = create_structure_unit(self.unit_type, structure, 'b')
        b1 = create_structure_unit(self.unit_type, structure, 'b1')
        b2 = create_structure_unit(self.unit_type, structure, 'b2')
        b1.parent = b
        b1.save()
        b2.parent = b
        b2.save()

        tag = Tag.objects.create()
        tv_type = TagVersionType.objects.create(name='volume')
        tv = TagVersion.objects.create(tag=tag, type=tv_type, elastic_index='component')
        TagStructure.objects.create(tag=tag, structure=structure, structure_unit=b1)

        response = self.client.get(self.url)
        data = response.data

        def find_unit(ref_code):
            return next(u for u in data if u["reference_code"] == ref_code)

        with self.subTest('a'):
            unit = find_unit('a')
            self.assertFalse(unit['is_unit_leaf_node'])
            self.assertTrue(unit['is_tag_leaf_node'])
            self.assertFalse(unit['is_leaf_node'])

        with self.subTest('a1'):
            unit = find_unit('a1')
            self.assertTrue(unit['is_unit_leaf_node'])
            self.assertTrue(unit['is_tag_leaf_node'])
            self.assertTrue(unit['is_leaf_node'])

        with self.subTest('b'):
            unit = find_unit('b')
            self.assertFalse(unit['is_unit_leaf_node'])
            self.assertTrue(unit['is_tag_leaf_node'])
            self.assertFalse(unit['is_leaf_node'])

        with self.subTest('b1'):
            unit = find_unit('b1')
            self.assertTrue(unit['is_unit_leaf_node'])
            self.assertFalse(unit['is_tag_leaf_node'])
            self.assertFalse(unit['is_leaf_node'])

        with self.subTest('b2'):
            unit = find_unit('b2')
            self.assertTrue(unit['is_unit_leaf_node'])
            self.assertTrue(unit['is_tag_leaf_node'])
            self.assertTrue(unit['is_leaf_node'])

        # delete TagVersion, keep structure
        tv.delete()

        response = self.client.get(self.url, {'ordering': 'name'})
        data = response.data

        with self.subTest('b1'):
            self.assertTrue(data[3]['is_unit_leaf_node'])
            self.assertTrue(data[3]['is_tag_leaf_node'])
            self.assertTrue(data[3]['is_leaf_node'])


class CreateStructureUnitTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        perm = Permission.objects.get(codename='add_structureunit')
        self.user.user_permissions.add(perm)

        self.client.force_authenticate(user=self.user)

        self.structure_type = StructureType.objects.create(name='test')

    def test_invalid_type(self):
        structure = create_structure(self.structure_type)
        other_structure_type = StructureType.objects.create(name='other')
        unit_type = StructureUnitType.objects.create(name="test", structure_type=other_structure_type)

        url = reverse('structure-units-list', args=[structure.pk])

        response = self.client.post(
            url,
            data={
                'name': 'foo',
                'type': unit_type.pk,
                'reference_code': '123',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(StructureUnit.objects.exists())

    def test_valid_type(self):
        structure = create_structure(self.structure_type)
        unit_type = StructureUnitType.objects.create(name="test", structure_type=structure.type)

        url = reverse('structure-units-list', args=[structure.pk])

        response = self.client.post(
            url,
            data={
                'name': 'foo',
                'type': unit_type.pk,
                'reference_code': '123',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(StructureUnit.objects.count(), 1)
        self.assertTrue(StructureUnit.objects.filter(structure=structure).exists())

    def test_with_related(self):
        structure = create_structure(self.structure_type)
        unit_type = StructureUnitType.objects.create(name="test", structure_type=structure.type)
        other_unit = StructureUnit.objects.create(
            name="foo", reference_code="123", type=unit_type,
            structure=structure,
        )
        relation_type = NodeRelationType.objects.create(name="test")
        url = reverse('structure-units-list', args=[structure.pk])

        response = self.client.post(
            url,
            data={
                'name': 'bar',
                'type': unit_type.pk,
                'reference_code': '456',
                'related_structure_units': [
                    {
                        'structure_unit': other_unit.pk,
                        'type': relation_type.pk,
                    }
                ],
            }
        )

        unit = StructureUnit.objects.get(name='bar')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(StructureUnit.objects.count(), 2)
        self.assertEqual(StructureUnitRelation.objects.count(), 2)

        self.assertTrue(
            StructureUnitRelation.objects.filter(
                structure_unit_a=unit, structure_unit_b=other_unit, type=relation_type
            ).exists()
        )
        self.assertTrue(
            StructureUnitRelation.objects.filter(
                structure_unit_a=other_unit, structure_unit_b=unit, type=relation_type
            ).exists()
        )

    def test_with_related_unit_and_mirrored_type(self):
        structure = create_structure(self.structure_type)
        unit_type = StructureUnitType.objects.create(name="test", structure_type=structure.type)
        other_unit = StructureUnit.objects.create(
            name="foo", reference_code="123", type=unit_type,
            structure=structure,
        )

        relation_type = NodeRelationType.objects.create(name="test")
        mirrored_relation_type = NodeRelationType.objects.create(name="test_mirrored")
        relation_type.mirrored_type = mirrored_relation_type
        relation_type.save()

        url = reverse('structure-units-list', args=[structure.pk])

        response = self.client.post(
            url,
            data={
                'name': 'bar',
                'type': unit_type.pk,
                'reference_code': '456',
                'related_structure_units': [
                    {
                        'structure_unit': other_unit.pk,
                        'type': relation_type.pk,
                    }
                ],
            }
        )

        unit = StructureUnit.objects.get(name='bar')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(StructureUnit.objects.count(), 2)
        self.assertEqual(StructureUnitRelation.objects.count(), 2)

        self.assertTrue(
            StructureUnitRelation.objects.filter(
                structure_unit_a=unit, structure_unit_b=other_unit, type=relation_type
            ).exists()
        )
        self.assertTrue(
            StructureUnitRelation.objects.filter(
                structure_unit_a=other_unit, structure_unit_b=unit, type=mirrored_relation_type
            ).exists()
        )

    def test_in_published_structure(self):
        structure = create_structure(self.structure_type)
        structure.published = True
        structure.save()
        unit_type = StructureUnitType.objects.create(name="test", structure_type=structure.type)

        url = reverse('structure-units-list', args=[structure.pk])

        response = self.client.post(
            url,
            data={
                'name': 'foo',
                'type': unit_type.pk,
                'reference_code': '123',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'non_field_errors': [PUBLISHED_STRUCTURE_CHANGE_ERROR]})

    def test_in_structure_template_instance(self):
        template = create_structure(self.structure_type)
        template.published = True
        template.save()

        instance = create_structure(self.structure_type)
        instance.is_template = False
        instance.published = True
        instance.template = template
        instance.save()

        unit_type = StructureUnitType.objects.create(name="test", structure_type=instance.type)
        url = reverse('structure-units-list', args=[instance.pk])

        response = self.client.post(
            url,
            data={
                'name': 'foo',
                'type': unit_type.pk,
                'reference_code': '123',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_in_structure_template_instance_with_permission_without_editable_flag(self):
        template = create_structure(self.structure_type)
        template.published = True
        template.save()

        instance = create_structure(self.structure_type)
        instance.is_template = False
        instance.published = True
        instance.template = template
        instance.save()

        unit_type = StructureUnitType.objects.create(name="test", structure_type=instance.type)
        url = reverse('structure-units-list', args=[instance.pk])

        perm = Permission.objects.get(codename='add_structureunit_instance')
        self.user.user_permissions.add(perm)
        response = self.client.post(
            url,
            data={
                'name': 'foo',
                'type': unit_type.pk,
                'reference_code': '123',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_in_structure_template_instance_with_permission_with_editable_flag(self):
        template = create_structure(self.structure_type)
        template.published = True
        template.save()

        instance = create_structure(self.structure_type)
        instance.is_template = False
        instance.published = True
        instance.template = template
        instance.save()

        instance.type.editable_instances = True
        instance.type.save()

        unit_type = StructureUnitType.objects.create(name="test", structure_type=instance.type)
        url = reverse('structure-units-list', args=[instance.pk])

        perm = Permission.objects.get(codename='add_structureunit_instance')
        self.user.user_permissions.add(perm)
        response = self.client.post(
            url,
            data={
                'name': 'foo',
                'type': unit_type.pk,
                'reference_code': '123',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class UpdateStructureUnitTemplateTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        perm = Permission.objects.get(codename='change_structureunit')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        self.structure_type = StructureType.objects.create(name='test')
        self.structure_unit_type = StructureUnitType.objects.create(name='test', structure_type=self.structure_type)

    def test_update(self):
        structure = create_structure(self.structure_type)
        structure_unit = create_structure_unit(self.structure_unit_type, structure, "1")
        url = reverse('structure-units-detail', args=[structure.pk, structure_unit.pk])

        response = self.client.patch(
            url,
            data={
                'name': 'bar',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(StructureUnit.objects.count(), 1)
        self.assertTrue(StructureUnit.objects.filter(name='bar').exists())

    def test_update_in_published_structure(self):
        structure = create_structure(self.structure_type)
        structure.published = True
        structure.save()

        structure_unit = create_structure_unit(self.structure_unit_type, structure, "1")
        url = reverse('structure-units-detail', args=[structure.pk, structure_unit.pk])

        response = self.client.patch(
            url,
            data={
                'name': 'bar',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'non_field_errors': [PUBLISHED_STRUCTURE_CHANGE_ERROR]})

        # relations can be changed even on published structures
        other_structure_unit = create_structure_unit(self.structure_unit_type, structure, "2")
        relation_type = NodeRelationType.objects.create(name="test")
        response = self.client.patch(
            url,
            data={
                'related_structure_units': [
                    {
                        'structure_unit': other_structure_unit.pk,
                        'type': relation_type.pk,
                    }
                ],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # but not together with other data
        response = self.client.patch(
            url,
            data={
                'name': 'bar',
                'related_structure_units': [
                    {
                        'structure_unit': other_structure_unit.pk,
                        'type': relation_type.pk,
                    }
                ],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'non_field_errors': [PUBLISHED_STRUCTURE_CHANGE_ERROR]})

    def test_update_in_unpublished_structure(self):
        structure = create_structure(self.structure_type)
        structure.publish()
        structure.unpublish()

        structure_unit = create_structure_unit(self.structure_unit_type, structure, "1")
        url = reverse('structure-units-detail', args=[structure.pk, structure_unit.pk])

        response = self.client.patch(
            url,
            data={
                'name': 'bar',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'non_field_errors': [NON_EDITABLE_STRUCTURE_CHANGE_ERROR]})

        # relations can be changed even on published structures
        other_structure_unit = create_structure_unit(self.structure_unit_type, structure, "2")
        relation_type = NodeRelationType.objects.create(name="test")
        response = self.client.patch(
            url,
            data={
                'related_structure_units': [
                    {
                        'structure_unit': other_structure_unit.pk,
                        'type': relation_type.pk,
                    }
                ],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # but not together with other data
        response = self.client.patch(
            url,
            data={
                'name': 'bar',
                'related_structure_units': [
                    {
                        'structure_unit': other_structure_unit.pk,
                        'type': relation_type.pk,
                    }
                ],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'non_field_errors': [NON_EDITABLE_STRUCTURE_CHANGE_ERROR]})


class UpdateStructureUnitInstanceTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        perm = Permission.objects.get(codename='change_structureunit')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        self.structure_type = StructureType.objects.create(name='test')
        self.structure_unit_type = StructureUnitType.objects.create(name='test', structure_type=self.structure_type)

    def test_update_without_permission(self):
        instance = create_structure(self.structure_type)
        instance.is_template = False
        instance.save()

        structure_unit = create_structure_unit(self.structure_unit_type, instance, "1")
        url = reverse('structure-units-detail', args=[instance.pk, structure_unit.pk])

        response = self.client.patch(
            url,
            data={
                'name': 'bar',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_without_editable_flag(self):
        instance = create_structure(self.structure_type)
        instance.is_template = False
        instance.save()

        structure_unit = create_structure_unit(self.structure_unit_type, instance, "1")
        url = reverse('structure-units-detail', args=[instance.pk, structure_unit.pk])

        perm = Permission.objects.get(codename='change_structureunit_instance')
        self.user.user_permissions.add(perm)
        response = self.client.patch(
            url,
            data={
                'name': 'bar',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_with_editable_flag(self):
        instance = create_structure(self.structure_type)
        instance.is_template = False
        instance.save()

        instance.type.editable_instances = True
        instance.type.save()

        structure_unit = create_structure_unit(self.structure_unit_type, instance, "1")
        url = reverse('structure-units-detail', args=[instance.pk, structure_unit.pk])

        perm = Permission.objects.get(codename='change_structureunit_instance')
        self.user.user_permissions.add(perm)

        response = self.client.patch(
            url,
            data={
                'name': 'bar',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_move_without_permission(self):
        instance = create_structure(self.structure_type)
        instance.is_template = False
        instance.save()

        instance.type.editable_instances = True
        instance.type.save()

        structure_unit = create_structure_unit(self.structure_unit_type, instance, "1")
        url = reverse('structure-units-detail', args=[instance.pk, structure_unit.pk])

        parent = create_structure_unit(self.structure_unit_type, instance, "A")
        response = self.client.patch(
            url,
            data={
                'parent': parent.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_move_without_movable_flag(self):
        instance = create_structure(self.structure_type)
        instance.is_template = False
        instance.save()

        instance.type.save()

        structure_unit = create_structure_unit(self.structure_unit_type, instance, "1")
        url = reverse('structure-units-detail', args=[instance.pk, structure_unit.pk])

        perm = Permission.objects.get(codename='move_structureunit_instance')
        self.user.user_permissions.add(perm)
        self.user = refresh_user(self.user)
        self.client.force_authenticate(user=self.user)
        parent = create_structure_unit(self.structure_unit_type, instance, "A")
        response = self.client.patch(
            url,
            data={
                'parent': parent.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_move_with_movable_flag(self):
        instance = create_structure(self.structure_type)
        instance.is_template = False
        instance.save()

        instance.type.movable_instance_units = True
        instance.type.save()

        structure_unit = create_structure_unit(self.structure_unit_type, instance, "1")
        url = reverse('structure-units-detail', args=[instance.pk, structure_unit.pk])

        perm = Permission.objects.get(codename='move_structureunit_instance')
        self.user.user_permissions.add(perm)
        self.user = refresh_user(self.user)
        self.client.force_authenticate(user=self.user)
        parent = create_structure_unit(self.structure_unit_type, instance, "A")

        response = self.client.patch(
            url,
            data={
                'parent': parent.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_move_to_structure_unit_with_tag(self):
        instance = create_structure(self.structure_type)
        instance.is_template = False
        instance.save()

        instance.type.movable_instance_units = True
        instance.type.save()

        structure_unit = create_structure_unit(self.structure_unit_type, instance, "1")
        url = reverse('structure-units-detail', args=[instance.pk, structure_unit.pk])

        self.user.is_superuser = True
        self.user.save()
        self.client.force_authenticate(user=self.user)
        parent = create_structure_unit(self.structure_unit_type, instance, "A")

        tag = Tag.objects.create()
        tv_type = TagVersionType.objects.create(name='volume')
        TagVersion.objects.create(tag=tag, type=tv_type, elastic_index='component')
        TagStructure.objects.create(tag=tag, structure=parent.structure, structure_unit=parent)

        response = self.client.patch(
            url,
            data={
                'parent': parent.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RelatedStructureUnitTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

        cls.user = User.objects.create(username='user')
        cls.member = cls.user.essauth_member

        perms = Permission.objects.filter(codename__in=[
            'add_structureunit', 'change_structureunit', 'change_structureunit_instance'
        ])
        cls.user.user_permissions.add(*perms)

        cls.structure_type = StructureType.objects.create(name='test', editable_instance_relations=True)
        cls.unit_type = StructureUnitType.objects.create(name="test", structure_type=cls.structure_type)
        cls.relation_type = NodeRelationType.objects.create(name="test")

    def test_relate_instance_to_instance_in_other_archive(self):
        '''
        Related instances must be part of the same archive
        '''

        self.client.force_authenticate(user=self.user)

        structure_instance = create_structure(self.structure_type, template=False)
        unit = StructureUnit.objects.create(
            name="foo", reference_code="123", type=self.unit_type,
            structure=structure_instance,
        )
        archive = Tag.objects.create()
        TagStructure.objects.create(tag=archive, structure=structure_instance)

        other_structure_instance = create_structure(self.structure_type, template=False)
        other_unit = StructureUnit.objects.create(
            name="bar", reference_code="123", type=self.unit_type,
            structure=other_structure_instance,
        )
        other_archive = Tag.objects.create()
        TagStructure.objects.create(tag=other_archive, structure=other_structure_instance)

        url = reverse('structure-units-detail', args=[structure_instance.pk, unit.pk])
        response = self.client.patch(
            url,
            data={
                'related_structure_units': [
                    {
                        'structure_unit': other_unit.pk,
                        'type': self.relation_type.pk,
                    }
                ],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_relate_instance_to_instance(self):
        self.client.force_authenticate(user=self.user)

        structure_instance = create_structure(self.structure_type, template=False)
        unit = StructureUnit.objects.create(
            name="foo", reference_code="123", type=self.unit_type,
            structure=structure_instance,
        )

        other_structure_instance = create_structure(self.structure_type, template=False)
        other_unit = StructureUnit.objects.create(
            name="bar", reference_code="123", type=self.unit_type,
            structure=other_structure_instance,
        )

        archive = Tag.objects.create()
        archive_descendant = Tag.objects.create()
        archive_nested_descendant = Tag.objects.create()

        archive_structure = TagStructure.objects.create(tag=archive, structure=structure_instance)
        archive_descendant_structure = TagStructure.objects.create(
            tag=archive_descendant, structure=structure_instance, structure_unit=unit,
            parent=archive_structure,
        )
        TagStructure.objects.create(
            tag=archive_nested_descendant, structure=structure_instance, parent=archive_descendant_structure,
        )

        TagStructure.objects.create(tag=archive, structure=other_structure_instance)

        url = reverse('structure-units-detail', args=[structure_instance.pk, unit.pk])
        response = self.client.patch(
            url,
            data={
                'related_structure_units': [
                    {
                        'structure_unit': other_unit.pk,
                        'type': self.relation_type.pk,
                    }
                ],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_relate_instance_to_template(self):
        self.client.force_authenticate(user=self.user)

        archive = Tag.objects.create()

        dst_structure_template = create_structure(self.structure_type, template=True)
        dst_structure_instance = create_structure(self.structure_type, template=False)
        dst_structure_instance.template = dst_structure_template
        dst_structure_instance.save()

        dst_template_unit = StructureUnit.objects.create(
            name="foo", reference_code="123", type=self.unit_type,
            structure=dst_structure_template,
        )
        dst_instance_unit = StructureUnit.objects.create(
            name="foo", reference_code="123", type=self.unit_type,
            structure=dst_structure_instance,
        )
        archive_structure = TagStructure.objects.create(tag=archive, structure=dst_structure_instance)

        src_structure_instance = create_structure(self.structure_type, template=False)
        src_instance_unit = StructureUnit.objects.create(
            name="bar", reference_code="456", type=self.unit_type,
            structure=src_structure_instance,
        )

        archive_descendant = Tag.objects.create()
        archive_nested_descendant = Tag.objects.create()

        archive_structure = TagStructure.objects.create(tag=archive, structure=src_structure_instance)
        archive_descendant_structure = TagStructure.objects.create(
            tag=archive_descendant, structure=src_structure_instance, structure_unit=src_instance_unit,
            parent=archive_structure,
        )
        TagStructure.objects.create(
            tag=archive_nested_descendant, structure=src_structure_instance, parent=archive_descendant_structure,
        )

        url = reverse('structure-units-detail', args=[src_structure_instance.pk, src_instance_unit.pk])
        response = self.client.patch(
            url,
            data={
                'related_structure_units': [
                    {
                        'structure_unit': dst_template_unit.pk,
                        'type': self.relation_type.pk,
                    }
                ],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # ensure unit descendants are not copied
        self.assertFalse(TagStructure.objects.filter(structure_unit=dst_template_unit).exists())

        # ensure unit descendants are copied to already existing instances of template
        self.assertTrue(TagStructure.objects.filter(structure_unit=dst_instance_unit).exists())

    def test_relate_instance_to_instance_same_structure(self):
        self.client.force_authenticate(user=self.user)

        structure_instance = create_structure(self.structure_type, template=False)
        unit = StructureUnit.objects.create(
            name="foo", reference_code="123", type=self.unit_type,
            structure=structure_instance,
        )

        other_unit = StructureUnit.objects.create(
            name="bar", reference_code="456", type=self.unit_type,
            structure=structure_instance,
        )

        archive = Tag.objects.create()
        archive_descendant = Tag.objects.create()
        archive_nested_descendant = Tag.objects.create()

        archive_structure = TagStructure.objects.create(tag=archive, structure=structure_instance)
        archive_descendant_structure = TagStructure.objects.create(
            tag=archive_descendant, structure=structure_instance, structure_unit=unit,
            parent=archive_structure,
        )
        TagStructure.objects.create(
            tag=archive_nested_descendant, structure=structure_instance, parent=archive_descendant_structure,
        )

        url = reverse('structure-units-detail', args=[structure_instance.pk, unit.pk])
        response = self.client.patch(
            url,
            data={
                'related_structure_units': [
                    {
                        'structure_unit': other_unit.pk,
                        'type': self.relation_type.pk,
                    }
                ],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # ensure unit descendants are not copied
        self.assertFalse(TagStructure.objects.filter(structure_unit=other_unit).exists())

    def test_relate_template_to_template(self):
        self.client.force_authenticate(user=self.user)

        structure_instance = create_structure(self.structure_type, template=True)
        unit = StructureUnit.objects.create(
            name="foo", reference_code="123", type=self.unit_type,
            structure=structure_instance,
        )

        other_structure_instance = create_structure(self.structure_type, template=True)
        other_unit = StructureUnit.objects.create(
            name="bar", reference_code="123", type=self.unit_type,
            structure=other_structure_instance,
        )

        url = reverse('structure-units-detail', args=[structure_instance.pk, unit.pk])
        response = self.client.patch(
            url,
            data={
                'related_structure_units': [
                    {
                        'structure_unit': other_unit.pk,
                        'type': self.relation_type.pk,
                    }
                ],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(StructureUnitRelation.objects.count(), 2)
        self.assertTrue(
            StructureUnitRelation.objects.filter(
                structure_unit_a=unit, structure_unit_b=other_unit, type=self.relation_type
            ).exists()
        )
        self.assertTrue(
            StructureUnitRelation.objects.filter(
                structure_unit_a=other_unit, structure_unit_b=unit, type=self.relation_type
            ).exists()
        )


class DeleteStructureUnitInstanceTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        perm = Permission.objects.get(codename='delete_structureunit')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        self.structure_type = StructureType.objects.create(name='test')
        self.structure_unit_type = StructureUnitType.objects.create(name='test', structure_type=self.structure_type)

    def test_delete_without_permission(self):
        instance = create_structure(self.structure_type)
        instance.is_template = False
        instance.save()

        structure_unit = create_structure_unit(self.structure_unit_type, instance, "1")
        url = reverse('structure-units-detail', args=[instance.pk, structure_unit.pk])

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_without_editable_flag(self):
        instance = create_structure(self.structure_type)
        instance.is_template = False
        instance.save()

        structure_unit = create_structure_unit(self.structure_unit_type, instance, "1")
        url = reverse('structure-units-detail', args=[instance.pk, structure_unit.pk])

        perm = Permission.objects.get(codename='delete_structureunit_instance')
        self.user.user_permissions.add(perm)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_with_editable_flag(self):
        instance = create_structure(self.structure_type)
        instance.is_template = False
        instance.save()

        instance.type.editable_instances = True
        instance.type.save()

        structure_unit = create_structure_unit(self.structure_unit_type, instance, "1")
        url = reverse('structure-units-detail', args=[instance.pk, structure_unit.pk])

        perm = Permission.objects.get(codename='delete_structureunit_instance')
        self.user.user_permissions.add(perm)

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class AgentArchiveRelationTests(TestCase):
    fixtures = ['countries_data', 'languages_data']

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.client.force_authenticate(user=self.user)

        self.archive_type = TagVersionType.objects.create(name='archive', archive_type=True)

        self.main_agent_type = MainAgentType.objects.create()
        self.agent_type = AgentType.objects.create(main_type=self.main_agent_type)

        self.relation_type = AgentTagLinkRelationType.objects.create(name='test')

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

    def create_archive(self):
        tag = Tag.objects.create()
        tag_version = TagVersion.objects.create(
            tag=tag,
            elastic_index='archive',
            type=self.archive_type,
        )
        return tag_version

    def test_add_relation(self):
        agent = self.create_agent()
        archive = self.create_archive()

        url = reverse('agent-archives-list', args=[agent.pk])

        response = self.client.post(
            url,
            data={
                'archive': archive.pk,
                'type': self.relation_type.pk,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AgentTagLink.objects.count(), 1)
        self.assertTrue(AgentTagLink.objects.filter(agent=agent, tag=archive, type=self.relation_type).exists())

    def test_add_same_relation_twice(self):
        agent = self.create_agent()
        archive = self.create_archive()

        url = reverse('agent-archives-list', args=[agent.pk])

        response = self.client.post(
            url,
            data={
                'archive': archive.pk,
                'type': self.relation_type.pk,
            }
        )

        response = self.client.post(
            url,
            data={
                'archive': archive.pk,
                'type': self.relation_type.pk,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(AgentTagLink.objects.count(), 1)

    def test_update_relation(self):
        agent = self.create_agent()
        archive = self.create_archive()
        relation = AgentTagLink.objects.create(
            agent=agent,
            tag=archive,
            type=self.relation_type,
            description='foo',
        )

        url = reverse('agent-archives-detail', args=[agent.pk, relation.pk])
        response = self.client.patch(
            url,
            data={
                'description': 'bar',
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AgentTagLink.objects.count(), 1)
        self.assertTrue(
            AgentTagLink.objects.filter(
                agent=agent,
                tag=archive,
                type=self.relation_type,
                description='bar',
            ).exists()
        )

    def test_delete_relation(self):
        agent = self.create_agent()
        archive = self.create_archive()
        relation = AgentTagLink.objects.create(
            agent=agent,
            tag=archive,
            type=self.relation_type,
        )

        url = reverse('agent-archives-detail', args=[agent.pk, relation.pk])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(AgentTagLink.objects.count(), 0)


class CreateArchiveTests(TestCase):
    fixtures = ['countries_data', 'languages_data']

    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')
        cls.archive_type = TagVersionType.objects.create(name='archive', archive_type=True)
        cls.url = reverse('search-list')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

    def test_without_permission(self):
        response = self.client.post(
            self.url,
            data={
                'index': 'archive',
            }
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch('ESSArch_Core.tags.search.TagVersionNestedSerializer')
    @mock.patch('ESSArch_Core.tags.search.ArchiveWriteSerializer')
    def test_with_permission(self, mock_write_serializer, mock_tag_serializer):
        self.user.user_permissions.add(Permission.objects.get(codename="create_archive"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        mock_tag_serializer().data = {}

        response = self.client.post(
            self.url,
            data={
                'index': 'archive',
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_write_serializer.assert_called_once()


class CreateComponentTests(TestCase):
    fixtures = ['countries_data', 'languages_data']

    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')
        cls.tag_type = TagVersionType.objects.create(name='volume', archive_type=False)
        cls.url = reverse('search-list')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

    def test_without_permission(self):
        response = self.client.post(
            self.url,
            data={
                'index': 'component',
            }
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch('ESSArch_Core.tags.search.TagVersionNestedSerializer')
    @mock.patch('ESSArch_Core.tags.search.ComponentWriteSerializer')
    def test_with_permission(self, mock_write_serializer, mock_tag_serializer):
        self.user.user_permissions.add(Permission.objects.get(codename="add_tag"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        mock_tag_serializer().data = {}

        response = self.client.post(
            self.url,
            data={
                'index': 'component',
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_write_serializer.assert_called_once()


class ChangeTagTests(TestCase):
    fixtures = ['countries_data', 'languages_data']

    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

    def test_change_archive_without_permission(self):
        archive_tag = Tag.objects.create()
        archive_type = TagVersionType.objects.create(name='archive', archive_type=True)
        archive_tag_version = TagVersion.objects.create(tag=archive_tag, type=archive_type, elastic_index='archive')

        url = reverse('search-detail', args=(archive_tag_version.pk,))

        response = self.client.patch(url, {'name': 'new name'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch('ESSArch_Core.tags.serializers.Archive.save')
    def test_change_archive_with_permission(self, mock_save):
        self.user.user_permissions.add(Permission.objects.get(codename="change_archive"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        archive_tag = Tag.objects.create()
        archive_type = TagVersionType.objects.create(name='archive', archive_type=True)
        archive_tag_version = TagVersion.objects.create(tag=archive_tag, type=archive_type, elastic_index='archive')

        url = reverse('search-detail', args=(archive_tag_version.pk,))

        response = self.client.patch(url, {'name': 'new name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch('ESSArch_Core.tags.serializers.Archive.save')
    def test_change_archive_delete_structure(self, mock_save):
        self.user.user_permissions.add(Permission.objects.get(codename="change_archive"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        structure_type = StructureType.objects.create(name='foo')
        structure_template1 = Structure.objects.create(name='template1', type=structure_type, is_template=True)
        structure_template1.publish()
        structure_instance1 = Structure.objects.create(
            name="instance1", type=structure_type,
            is_template=False, template=structure_template1,
        )

        structure_template2 = Structure.objects.create(name='template2', type=structure_type, is_template=True)
        structure_template2.publish()
        structure_instance2 = Structure.objects.create(
            name="instance2", type=structure_type,
            is_template=False, template=structure_template2,
        )

        archive_tag = Tag.objects.create()
        archive_type = TagVersionType.objects.create(name='archive', archive_type=True)
        archive_tag_version = TagVersion.objects.create(tag=archive_tag, type=archive_type, elastic_index='archive')
        archive_tag_structure1 = TagStructure.objects.create(tag=archive_tag, structure=structure_instance1)
        TagStructure.objects.create(tag=archive_tag, structure=structure_instance2)

        component_tag = Tag.objects.create()
        component_type = TagVersionType.objects.create(name='component')
        TagVersion.objects.create(
            tag=component_tag, type=component_type,
            elastic_index='component',
        )
        TagStructure.objects.create(
            tag=component_tag, structure=structure_instance1,
            parent=archive_tag_structure1,
        )

        url = reverse('search-detail', args=(archive_tag_version.pk,))

        with self.subTest('delete non-empty structure'):
            response = self.client.patch(url, {'structures': [
                structure_template2.pk,
            ]})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(TagStructure.objects.filter(tag=archive_tag).count(), 2)

        with self.subTest('delete empty structure'):
            response = self.client.patch(url, {'structures': [
                structure_template1.pk,
            ]})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(TagStructure.objects.filter(tag=archive_tag).count(), 1)

    def test_change_component_without_permission(self):
        tag = Tag.objects.create()
        tag_type = TagVersionType.objects.create(name='volume', archive_type=False)
        tag_version = TagVersion.objects.create(tag=tag, type=tag_type, elastic_index='component')

        url = reverse('search-detail', args=(tag_version.pk,))

        response = self.client.patch(url, {'name': 'new name'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch('ESSArch_Core.tags.serializers.Component.save')
    def test_change_component_with_permission(self, mock_save):
        self.user.user_permissions.add(Permission.objects.get(codename="change_tag"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        tag = Tag.objects.create()
        tag_type = TagVersionType.objects.create(name='volume', archive_type=False)
        tag_version = TagVersion.objects.create(tag=tag, type=tag_type, elastic_index='component')

        url = reverse('search-detail', args=(tag_version.pk,))

        response = self.client.patch(url, {'name': 'new name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DeleteTagTests(TestCase):
    fixtures = ['countries_data', 'languages_data']

    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

    def test_delete_archive_without_permission(self):
        archive_tag = Tag.objects.create()
        archive_type = TagVersionType.objects.create(name='archive', archive_type=True)
        archive_tag_version = TagVersion.objects.create(tag=archive_tag, type=archive_type, elastic_index='archive')

        url = reverse('search-detail', args=(archive_tag_version.pk,))

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        archive_tag_version.refresh_from_db()

    @mock.patch('ESSArch_Core.tags.signals.TagVersion.get_doc')
    def test_delete_archive_with_permission(self, mock_signal):
        self.user.user_permissions.add(Permission.objects.get(codename="delete_archive"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        archive_tag = Tag.objects.create()
        archive_type = TagVersionType.objects.create(name='archive', archive_type=True)
        archive_tag_version = TagVersion.objects.create(tag=archive_tag, type=archive_type, elastic_index='archive')

        url = reverse('search-detail', args=(archive_tag_version.pk,))

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with self.assertRaises(TagVersion.DoesNotExist):
            archive_tag_version.refresh_from_db()

        with self.assertRaises(Tag.DoesNotExist):
            archive_tag.refresh_from_db()

    def test_delete_component_without_permission(self):
        tag = Tag.objects.create()
        tag_type = TagVersionType.objects.create(name='volume', archive_type=False)
        tag_version = TagVersion.objects.create(tag=tag, type=tag_type, elastic_index='component')

        url = reverse('search-detail', args=(tag_version.pk,))

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        tag_version.refresh_from_db()

    @mock.patch('ESSArch_Core.tags.signals.TagVersion.get_doc')
    def test_delete_component_with_permission(self, mock_signal):
        self.user.user_permissions.add(Permission.objects.get(codename="delete_tag"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        tag_type = TagVersionType.objects.create(name='volume', archive_type=False)

        with self.subTest('single version'):
            tag = Tag.objects.create()
            tag_version = TagVersion.objects.create(tag=tag, type=tag_type, elastic_index='component')

            url = reverse('search-detail', args=(tag_version.pk,))
            response = self.client.delete(url)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

            with self.assertRaises(TagVersion.DoesNotExist):
                tag_version.refresh_from_db()

            with self.assertRaises(Tag.DoesNotExist):
                tag.refresh_from_db()

        with self.subTest('multiple versions'):
            tag = Tag.objects.create()
            tag_version = TagVersion.objects.create(tag=tag, type=tag_type, elastic_index='component')
            tag_version2 = TagVersion.objects.create(tag=tag, type=tag_type, elastic_index='component')

            url = reverse('search-detail', args=(tag_version.pk,))
            response = self.client.delete(url)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

            with self.assertRaises(TagVersion.DoesNotExist):
                tag_version.refresh_from_db()

            tag_version2.refresh_from_db()
            tag.refresh_from_db()


class CreateDeliveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')
        cls.delivery_type = DeliveryType.objects.create(name='test')
        cls.url = reverse('delivery-list')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

    def test_without_permission(self):
        response = self.client.post(
            self.url,
            data={
                'name': 'test',
                'type': self.delivery_type.pk,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_with_permission(self):
        EventType.objects.create(eventType='20300', category=EventType.CATEGORY_DELIVERY)
        self.user.user_permissions.add(Permission.objects.get(codename="add_delivery"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            data={
                'name': 'test',
                'type': self.delivery_type.pk,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(reverse('delivery-detail', args=(Delivery.objects.get().pk,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ChangeDeliveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')
        cls.delivery_type = DeliveryType.objects.create(name='test')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

    def create_delivery(self):
        delivery = Delivery.objects.create(
            name='test',
            type=self.delivery_type,
        )

        self.group.add_object(delivery)
        return delivery

    def test_without_permission(self):
        delivery = self.create_delivery()
        url = reverse('delivery-detail', args=(delivery.pk,))
        response = self.client.patch(
            url,
            data={
                'name': 'new name',
            }
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_with_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename="change_delivery"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        delivery = self.create_delivery()
        url = reverse('delivery-detail', args=(delivery.pk,))
        response = self.client.patch(
            url,
            data={
                'name': 'new name',
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DeleteDeliveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')
        cls.delivery_type = DeliveryType.objects.create(name='test')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

    def create_delivery(self):
        delivery = Delivery.objects.create(
            name='test',
            type=self.delivery_type,
        )

        self.group.add_object(delivery)
        return delivery

    def test_without_permission(self):
        delivery = self.create_delivery()
        url = reverse('delivery-detail', args=(delivery.pk,))
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_with_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename="delete_delivery"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        delivery = self.create_delivery()
        url = reverse('delivery-detail', args=(delivery.pk,))
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class CreateTransferTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')
        cls.delivery_type = DeliveryType.objects.create(name='test')
        cls.url = reverse('transfer-list')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

    def create_delivery(self):
        delivery = Delivery.objects.create(
            name='test',
            type=self.delivery_type,
        )

        self.group.add_object(delivery)
        return delivery

    def test_without_permission(self):
        delivery = self.create_delivery()
        response = self.client.post(
            self.url,
            data={
                'name': 'test',
                'delivery': delivery.pk,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_with_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename="add_transfer"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        delivery = self.create_delivery()
        response = self.client.post(
            self.url,
            data={
                'name': 'test',
                'delivery': delivery.pk,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(reverse('transfer-detail', args=(Transfer.objects.get().pk,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ChangeTransferTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')
        cls.delivery_type = DeliveryType.objects.create(name='test')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

    def create_delivery(self):
        delivery = Delivery.objects.create(
            name='test',
            type=self.delivery_type,
        )

        self.group.add_object(delivery)
        return delivery

    def create_transfer(self, delivery):
        transfer = Transfer.objects.create(
            name='test',
            delivery=delivery,
        )

        self.group.add_object(transfer)
        return transfer

    def test_without_permission(self):
        delivery = self.create_delivery()
        transfer = self.create_transfer(delivery)
        url = reverse('transfer-detail', args=(transfer.pk,))
        response = self.client.patch(
            url,
            data={
                'name': 'new name',
            }
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_with_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename="change_transfer"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        delivery = self.create_delivery()
        transfer = self.create_transfer(delivery)
        url = reverse('transfer-detail', args=(transfer.pk,))
        response = self.client.patch(
            url,
            data={
                'name': 'new name',
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DeleteTransferTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')
        cls.delivery_type = DeliveryType.objects.create(name='test')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

    def create_delivery(self):
        delivery = Delivery.objects.create(
            name='test',
            type=self.delivery_type,
        )

        self.group.add_object(delivery)
        return delivery

    def create_transfer(self, delivery):
        transfer = Transfer.objects.create(
            name='test',
            delivery=delivery,
        )

        self.group.add_object(transfer)
        return transfer

    def test_without_permission(self):
        delivery = self.create_delivery()
        transfer = self.create_transfer(delivery)
        url = reverse('transfer-detail', args=(transfer.pk,))
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_with_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename="delete_transfer"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        delivery = self.create_delivery()
        transfer = self.create_transfer(delivery)
        url = reverse('transfer-detail', args=(transfer.pk,))
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class CreateLocationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')
        cls.location_function_type = LocationFunctionType.objects.create(name='test')
        cls.location_level_type = LocationLevelType.objects.create(name='test')
        cls.url = reverse('location-list')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        group = Group.objects.create(name='organization', group_type=self.org_group_type)
        group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

    def test_without_permission(self):
        response = self.client.post(
            self.url,
            data={
                'name': 'test',
                'function': self.location_function_type.pk,
                'level_type': self.location_level_type.pk,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_with_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename="add_location"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            data={
                'name': 'test',
                'function': self.location_function_type.pk,
                'level_type': self.location_level_type.pk,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(reverse('location-detail', args=(Location.objects.get().pk,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ChangeLocationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')
        cls.location_function_type = LocationFunctionType.objects.create(name='test')
        cls.location_level_type = LocationLevelType.objects.create(name='test')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

    def create_location(self):
        location = Location.objects.create(
            name='test',
            function=self.location_function_type,
            level_type=self.location_level_type,
        )

        self.group.add_object(location)
        return location

    def test_without_permission(self):
        location = self.create_location()
        url = reverse('location-detail', args=(location.pk,))
        response = self.client.patch(
            url,
            data={
                'name': 'new name',
            }
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_with_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename="change_location"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        delivery = self.create_location()
        url = reverse('location-detail', args=(delivery.pk,))
        response = self.client.patch(
            url,
            data={
                'name': 'new name',
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DeleteLocationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')
        cls.location_function_type = LocationFunctionType.objects.create(name='test')
        cls.location_level_type = LocationLevelType.objects.create(name='test')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

    def create_location(self):
        location = Location.objects.create(
            name='test',
            function=self.location_function_type,
            level_type=self.location_level_type,
        )

        self.group.add_object(location)
        return location

    def test_without_permission(self):
        location = self.create_location()
        url = reverse('location-detail', args=(location.pk,))
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_with_permission(self):
        self.user.user_permissions.add(Permission.objects.get(codename="delete_location"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        location = self.create_location()
        url = reverse('location-detail', args=(location.pk,))
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class AddNodeToLocationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')
        cls.location_function_type = LocationFunctionType.objects.create(name='test')
        cls.location_level_type = LocationLevelType.objects.create(name='test')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

    def create_location(self):
        location = Location.objects.create(
            name='test',
            function=self.location_function_type,
            level_type=self.location_level_type,
        )

        self.group.add_object(location)
        return location

    def test_without_permission(self):
        location = self.create_location()

        tag = Tag.objects.create()
        tag_type = TagVersionType.objects.create(name='volume', archive_type=False)
        tag_version = TagVersion.objects.create(tag=tag, type=tag_type, elastic_index='component')

        url = reverse('search-detail', args=(tag_version.pk,))
        response = self.client.patch(url, {'location': location.pk})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch('ESSArch_Core.tags.serializers.Component.save')
    def test_with_permission(self, mock_save):
        self.user.user_permissions.add(Permission.objects.get(codename="change_tag_location"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        location = self.create_location()

        tag = Tag.objects.create()
        tag_type = TagVersionType.objects.create(name='volume', archive_type=False)
        tag_version = TagVersion.objects.create(tag=tag, type=tag_type, elastic_index='component')

        url = reverse('search-detail', args=(tag_version.pk,))
        response = self.client.patch(url, {'location': location.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ChangeNodeLocationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')
        cls.location_function_type = LocationFunctionType.objects.create(name='test')
        cls.location_level_type = LocationLevelType.objects.create(name='test')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

    def create_location(self):
        location = Location.objects.create(
            name='test',
            function=self.location_function_type,
            level_type=self.location_level_type,
        )

        self.group.add_object(location)
        return location

    def test_without_permission(self):
        location = self.create_location()
        new_location = self.create_location()

        tag = Tag.objects.create()
        tag_type = TagVersionType.objects.create(name='volume', archive_type=False)
        tag_version = TagVersion.objects.create(tag=tag, type=tag_type, location=location, elastic_index='component')

        url = reverse('search-detail', args=(tag_version.pk,))
        response = self.client.patch(url, {'location': new_location.pk})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch('ESSArch_Core.tags.serializers.Component.save')
    def test_with_permission(self, mock_save):
        self.user.user_permissions.add(Permission.objects.get(codename="change_tag_location"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        location = self.create_location()
        new_location = self.create_location()

        tag = Tag.objects.create()
        tag_type = TagVersionType.objects.create(name='volume', archive_type=False)
        tag_version = TagVersion.objects.create(tag=tag, type=tag_type, location=location, elastic_index='component')

        url = reverse('search-detail', args=(tag_version.pk,))
        response = self.client.patch(url, {'location': new_location.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DeleteNodeLocationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_group_type = GroupType.objects.create(codename='organization')
        cls.location_function_type = LocationFunctionType.objects.create(name='test')
        cls.location_level_type = LocationLevelType.objects.create(name='test')

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.group = Group.objects.create(name='organization', group_type=self.org_group_type)
        self.group.add_member(self.member)

        self.client.force_authenticate(user=self.user)

    def create_location(self):
        location = Location.objects.create(
            name='test',
            function=self.location_function_type,
            level_type=self.location_level_type,
        )

        self.group.add_object(location)
        return location

    def test_without_permission(self):
        location = self.create_location()

        tag = Tag.objects.create()
        tag_type = TagVersionType.objects.create(name='volume', archive_type=False)
        tag_version = TagVersion.objects.create(tag=tag, type=tag_type, location=location, elastic_index='component')

        url = reverse('search-detail', args=(tag_version.pk,))
        response = self.client.patch(url, {'location': None})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch('ESSArch_Core.tags.serializers.Component.save')
    def test_with_permission(self, mock_save):
        self.user.user_permissions.add(Permission.objects.get(codename="change_tag_location"))
        self.user = User.objects.get(username="user")
        self.client.force_authenticate(user=self.user)

        location = self.create_location()

        tag = Tag.objects.create()
        tag_type = TagVersionType.objects.create(name='volume', archive_type=False)
        tag_version = TagVersion.objects.create(tag=tag, type=tag_type, location=location, elastic_index='component')

        url = reverse('search-detail', args=(tag_version.pk,))
        response = self.client.patch(url, {'location': None})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
