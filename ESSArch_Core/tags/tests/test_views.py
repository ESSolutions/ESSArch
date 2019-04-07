from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from ESSArch_Core.tags.models import (
    Structure,
    StructureType,
    StructureUnit,
    StructureUnitType,
)

User = get_user_model()


class ListStructureTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('structure-list')
        self.user = User.objects.create(username='user')
        self.client.force_authenticate(user=self.user)

        self.structure_type = StructureType.objects.create(name='test')

    def create_structure(self):
        return Structure.objects.create(type=self.structure_type, is_template=True)

    def test_empty(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_one_structure(self):
        self.create_structure()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_multiple_agents(self):
        self.create_structure()
        self.create_structure()

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
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Structure.objects.count(), 1)
        self.assertTrue(Structure.objects.filter(name='foo', created_by=self.user, revised_by=self.user).exists())


class UpdateStructureTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        self.client.force_authenticate(user=self.user)

        self.structure_type = StructureType.objects.create(name='test')

    def create_structure(self):
        return Structure.objects.create(type=self.structure_type, is_template=True)

    def test_without_permission(self):
        structure = self.create_structure()
        url = reverse('structure-detail', args=[structure.pk])

        response = self.client.patch(
            url,
            data={
                'name': 'bar',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update(self):
        structure = self.create_structure()
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


class CreateStructureUnitTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        perm = Permission.objects.get(codename='add_structureunit')
        self.user.user_permissions.add(perm)

        self.client.force_authenticate(user=self.user)

        self.structure_type = StructureType.objects.create(name='test')

    def create_structure(self):
        return Structure.objects.create(type=self.structure_type, is_template=True)

    def test_invalid_type(self):
        structure = self.create_structure()
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
        structure = self.create_structure()
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


class UpdateStructureUnitTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create(username='user')
        self.member = self.user.essauth_member

        perm = Permission.objects.get(codename='change_structureunit')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        self.structure_type = StructureType.objects.create(name='test')
        self.structure_unit_type = StructureUnitType.objects.create(name='test', structure_type=self.structure_type)

    def create_structure(self):
        return Structure.objects.create(type=self.structure_type, is_template=True)

    def create_structure_unit(self, structure):
        return StructureUnit.objects.create(structure=structure, type=self.structure_unit_type)

    def test_update(self):
        structure = self.create_structure()
        structure_unit = self.create_structure_unit(structure)
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
