import os
import shutil
import tempfile

from django.test import SimpleTestCase

from ESSArch_Core.storage.copy import copy_dir


class CopyDirTests(SimpleTestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def test_copy_trees(self):
        src = os.path.join(self.root, 'src')
        os.makedirs(os.path.join(src, 'a'))
        os.makedirs(os.path.join(src, 'b'))

        open(os.path.join(src, 'a', 'foo.txt'), 'a').close()
        open(os.path.join(src, 'b', 'bar.txt'), 'a').close()

        dst = os.path.join(self.root, 'dst')
        copy_dir(src, dst)

        self.assertTrue(os.path.isfile(os.path.join(dst, 'a/foo.txt')))
        self.assertTrue(os.path.isfile(os.path.join(dst, 'b/bar.txt')))

        # ensure source still exists
        self.assertTrue(os.path.isfile(os.path.join(src, 'a/foo.txt')))
        self.assertTrue(os.path.isfile(os.path.join(src, 'b/bar.txt')))

    def test_copy_empty_subdirs(self):
        src = os.path.join(self.root, 'src')
        os.makedirs(os.path.join(src, 'a'))
        os.makedirs(os.path.join(src, 'b'))

        dst = os.path.join(self.root, 'dst')
        copy_dir(src, dst)

        self.assertTrue(os.path.isdir(os.path.join(dst, 'a')))
        self.assertTrue(os.path.isdir(os.path.join(dst, 'b')))

        # ensure source still exists
        self.assertTrue(os.path.isdir(os.path.join(src, 'a')))
        self.assertTrue(os.path.isdir(os.path.join(src, 'b')))
