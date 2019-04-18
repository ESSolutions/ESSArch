from unittest import mock

from django.test import TestCase

from ESSArch_Core.tags.models import (
    NodeRelationType,
    Structure,
    StructureType,
    StructureUnit,
    StructureUnitType,
    StructureUnitRelation,
    Tag,
    TagStructure,
    TagVersion,
    TagVersionType,
)


class StructureTestCase(TestCase):
    def test_create_new_version(self):
        s_type = StructureType.objects.create()
        structure = Structure.objects.create(type=s_type, is_template=True, published=True)
        new_version = structure.create_new_version('2.0')

        # version link is the same and the new version is not published
        self.assertEqual(new_version.version_link, structure.version_link)
        self.assertFalse(new_version.published)

        # all units in the old version has a relation to structures in the new version
        for unit in structure.units.all():
            self.assertTrue(unit.related_structure_units.filter(structure=new_version).exists())

    def test_is_new_version(self):
        s_type = StructureType.objects.create()
        structure = Structure.objects.create(type=s_type, is_template=True, published=True)
        new_version = Structure.objects.create(
            type=s_type, is_template=True,
            version_link=structure.version_link,
        )

        self.assertFalse(structure.is_new_version())
        self.assertTrue(new_version.is_new_version())

    def test_publish(self):
        s_type = StructureType.objects.create()
        structure = Structure.objects.create(type=s_type, is_template=True)

        structure.publish()
        self.assertTrue(structure.published)
        self.assertIsNotNone(structure.published_date)

    def test_publish_new_version(self):
        s_type = StructureType.objects.create()
        structure = Structure.objects.create(type=s_type, is_template=True, published=True)
        new_version = Structure.objects.create(
            type=s_type, is_template=True,
            version_link=structure.version_link,
        )

        new_version.publish()

    def test_publish_new_version_with_units(self):
        s_type = StructureType.objects.create()
        su_type = StructureUnitType.objects.create(structure_type=s_type)
        structure = Structure.objects.create(type=s_type, is_template=True, published=True)
        unit = StructureUnit.objects.create(structure=structure, type=su_type)

        new_version = Structure.objects.create(
            type=s_type, is_template=True,
            version_link=structure.version_link,
        )
        new_unit = StructureUnit.objects.create(structure=new_version, type=su_type)

        with self.assertRaises(AssertionError):
            # no related unit created in new version
            new_version.publish()

        rel_type = NodeRelationType.objects.create()
        StructureUnitRelation.objects.create(
            structure_unit_a=unit,
            structure_unit_b=new_unit,
            type=rel_type,
        )

        new_version.publish()

    @mock.patch('ESSArch_Core.tags.documents.StructureUnitDocument')
    def test_publish_new_version_with_instances(self, mock_unit):
        s_type = StructureType.objects.create()
        su_type = StructureUnitType.objects.create(structure_type=s_type)
        structure = Structure.objects.create(type=s_type, is_template=True, published=True)
        unit = StructureUnit.objects.create(structure=structure, type=su_type)

        # create archive
        tag_type = TagVersionType.objects.create(name="test", archive_type=False)

        archive_tag = Tag.objects.create()
        TagVersion.objects.create(name="archive", tag=archive_tag, type=tag_type, elastic_index="test")
        structure_instance, archive_tag_structure = structure.create_template_instance(archive_tag)
        unit_instance = unit.instances.get()

        # create tags
        tag1 = Tag.objects.create()
        TagVersion.objects.create(name="tag1", tag=tag1, type=tag_type, elastic_index="test")
        tag1_structure = TagStructure.objects.create(
            tag=tag1, parent=archive_tag_structure,
            structure=structure_instance,
            structure_unit=unit_instance,
        )

        tag2 = Tag.objects.create()
        TagVersion.objects.create(name="tag2", tag=tag2, type=tag_type, elastic_index="test")
        TagStructure.objects.create(
            structure=structure_instance,
            tag=tag2, parent=tag1_structure
        )

        new_version = Structure.objects.create(
            type=s_type, is_template=True,
            version_link=structure.version_link,
        )
        new_unit = StructureUnit.objects.create(structure=new_version, type=su_type)

        rel_type = NodeRelationType.objects.create()
        StructureUnitRelation.objects.create(
            structure_unit_a=unit,
            structure_unit_b=new_unit,
            type=rel_type,
        )

        new_version.publish()

        # validate
        self.assertTrue(tag1.structures.filter(
            structure__template=new_version,
            structure_unit__template=new_unit,
        ).exists())

        self.assertTrue(tag2.structures.filter(
            structure__template=new_version,
            structure_unit__isnull=True,
            parent=tag1.structures.get(structure_unit__template=new_unit)
        ).exists())


class TagStructureTestCase(TestCase):
    def test_new_version_single_node(self):
        s_type = StructureType.objects.create()
        original_structure = Structure.objects.create(name="original", type=s_type, is_template=False)
        new_structure = Structure.objects.create(name="new", type=s_type, is_template=False)

        root_tag = Tag.objects.create()
        root_tag_structure = TagStructure.objects.create(tag=root_tag, structure=original_structure)

        new_root_tag_structure = root_tag_structure.create_new(new_structure)
        new_root_tag_structure.refresh_from_db()

        root_tag_structure.refresh_from_db()

        # verify the new tag
        self.assertEqual(new_root_tag_structure.tag, root_tag)
        self.assertEqual(new_root_tag_structure.structure, new_structure)
        self.assertNotEqual(new_root_tag_structure.tree_id, root_tag_structure.tree_id)
        self.assertEqual(new_root_tag_structure.get_descendant_count(), 0)

        # ensure that the old tag hasn't changed
        self.assertEqual(root_tag_structure.tag, root_tag)
        self.assertEqual(root_tag_structure.structure, original_structure)
        self.assertEqual(root_tag_structure.get_descendant_count(), 0)

    def test_new_version_tree(self):
        s_type = StructureType.objects.create()
        original_structure = Structure.objects.create(name="original", type=s_type, is_template=False)
        new_structure = Structure.objects.create(name="new", type=s_type, is_template=False)

        root_tag = Tag.objects.create()
        root_tag_structure = TagStructure.objects.create(tag=root_tag, structure=original_structure)
        child_tag = Tag.objects.create()
        child_tag_structure = TagStructure.objects.create(tag=child_tag, structure=original_structure,
                                                          parent=root_tag_structure)
        grandchild_tag = Tag.objects.create()
        grandchild_tag_structure = TagStructure.objects.create(tag=grandchild_tag, structure=original_structure,
                                                               parent=child_tag_structure)

        new_root_tag_structure = root_tag_structure.create_new(new_structure)
        new_root_tag_structure.refresh_from_db()

        root_tag_structure.refresh_from_db()
        child_tag_structure.refresh_from_db()
        grandchild_tag_structure.refresh_from_db()

        # verify the new root tag
        self.assertEqual(new_root_tag_structure.tag, root_tag)
        self.assertEqual(new_root_tag_structure.structure, new_structure)
        self.assertNotEqual(new_root_tag_structure.tree_id, root_tag_structure.tree_id)
        self.assertEqual(new_root_tag_structure.get_descendant_count(), 2)

        # the new root should only have a single child and that child should
        # point to the same tag as before
        self.assertEqual(new_root_tag_structure.get_children().count(), 1)
        self.assertNotEqual(new_root_tag_structure.get_children().get(), child_tag_structure)
        self.assertEqual(new_root_tag_structure.get_children().get().tag, child_tag)

        # the new child should only have a single child and that child should
        # point to the same tag as before
        self.assertEqual(new_root_tag_structure.get_children().get().get_children().count(), 1)
        self.assertNotEqual(new_root_tag_structure.get_children().get().get_children().get(), grandchild_tag_structure)
        self.assertEqual(new_root_tag_structure.get_children().get().get_children().get().tag, grandchild_tag)

        # ensure that the old tree hasn't changed
        self.assertEqual(root_tag_structure.tag, root_tag)
        self.assertEqual(root_tag_structure.structure, original_structure)
        self.assertEqual(root_tag_structure.get_children().count(), 1)
        self.assertEqual(root_tag_structure.get_descendant_count(), 2)
        self.assertEqual(root_tag_structure.get_children().get().tag, child_tag)
        self.assertEqual(root_tag_structure.get_children().get().get_children().count(), 1)
        self.assertEqual(root_tag_structure.get_children().get().get_children().get().tag, grandchild_tag)
