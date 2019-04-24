from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from ESSArch_Core.tags.models import (
    NodeRelationType,
    Structure,
    StructureType,
    StructureUnit,
    StructureUnitRelation,
    StructureUnitType,
    Tag,
    TagStructure,
)
from ESSArch_Core.tags.serializers import PUBLISHED_STRUCTURE_CHANGE_ERROR

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
        structure.published = True
        structure.save()
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

        perm = Permission.objects.get(codename='add_structure_unit_instance')
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

        perm = Permission.objects.get(codename='add_structure_unit_instance')
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

        perm = Permission.objects.get(codename='change_structure_unit_instance')
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

        perm = Permission.objects.get(codename='change_structure_unit_instance')
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

        perm = Permission.objects.get(codename='move_structure_unit_instance')
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

        perm = Permission.objects.get(codename='move_structure_unit_instance')
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


class RelatedStructureUnitTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

        cls.user = User.objects.create(username='user')
        cls.member = cls.user.essauth_member

        perms = Permission.objects.filter(codename__in=[
            'add_structureunit', 'change_structureunit', 'change_structure_unit_instance'
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

        other_archive_structure = TagStructure.objects.create(tag=archive, structure=other_structure_instance)

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

        # ensure unit descendants are copied
        first_level = TagStructure.objects.filter(
            tag=archive_descendant, parent=other_archive_structure, structure=other_structure_instance,
            structure_unit=other_unit,
        )
        self.assertTrue(first_level.exists())
        self.assertTrue(
            TagStructure.objects.filter(
                tag=archive_nested_descendant, parent=first_level.get(), structure=other_structure_instance
            ).exists()
        )

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

        perm = Permission.objects.get(codename='delete_structure_unit_instance')
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

        perm = Permission.objects.get(codename='delete_structure_unit_instance')
        self.user.user_permissions.add(perm)

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
