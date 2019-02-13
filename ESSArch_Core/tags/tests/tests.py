from django.test import TestCase

from ESSArch_Core.tags.models import Structure, Tag, TagStructure


class TagStructureTestCase(TestCase):
    def test_new_version_single_node(self):
        original_structure = Structure.objects.create(name="original")
        new_structure = Structure.objects.create(name="new")

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
        original_structure = Structure.objects.create(name="original")
        new_structure = Structure.objects.create(name="new")

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
