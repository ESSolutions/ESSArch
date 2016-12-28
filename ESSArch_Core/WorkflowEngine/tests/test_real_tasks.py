# -*- coding: utf-8 -*-

import os
import shutil
import traceback

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

try:
    from install.install_default_config_etp import installDefaultEventTypes
except ImportError:
    from install.install_default_config_eta import installDefaultEventTypes

from ESSArch_Core.ip.models import (
    InformationPackage,
)

from ESSArch_Core.WorkflowEngine.models import (
    ProcessTask,
)


def setUpModule():
    installDefaultEventTypes()
    settings.CELERY_ALWAYS_EAGER = True
    settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = False


class CalculateChecksumTestCase(TestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.CalculateChecksum"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

        self.fname = os.path.join(self.datadir, "file1.txt")

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_file_with_content(self):
        with open(self.fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname
            }
        )

        expected = "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
        actual = task.run().get().get(task.pk)

        self.assertEqual(expected, actual)

    def test_empty_file(self):
        open(self.fname, "a").close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname
            }
        )

        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        actual = task.run().get().get(task.pk)

        self.assertEqual(expected, actual)

    def test_small_block_size(self):
        with open(self.fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'block_size': 1
            }
        )

        expected = "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
        actual = task.run().get().get(task.pk)

        self.assertEqual(expected, actual)

    def test_md5(self):
        with open(self.fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'algorithm': 'MD5'
            }
        )

        expected = "acbd18db4cc2f85cedef654fccc4a4d8"
        actual = task.run().get().get(task.pk)

        self.assertEqual(expected, actual)

    def test_sha1(self):
        with open(self.fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'algorithm': 'SHA-1'
            }
        )

        expected = "0beec7b5ea3f0fdbc95d0dd47f3c5bc275da8a33"
        actual = task.run().get().get(task.pk)

        self.assertEqual(expected, actual)

    def test_sha224(self):
        with open(self.fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'algorithm': 'SHA-224'
            }
        )

        expected = "0808f64e60d58979fcb676c96ec938270dea42445aeefcd3a4e6f8db"
        actual = task.run().get().get(task.pk)

        self.assertEqual(expected, actual)

    def test_sha384(self):
        with open(self.fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'algorithm': 'SHA-384'
            }
        )

        expected = "98c11ffdfdd540676b1a137cb1a22b2a70350c9a44171d6b1180c6be5cbb2ee3f79d532c8a1dd9ef2e8e08e752a3babb"
        actual = task.run().get().get(task.pk)

        self.assertEqual(expected, actual)

    def test_sha512(self):
        with open(self.fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'algorithm': 'SHA-512'
            }
        )

        expected = "f7fbba6e0636f890e56fbbf3283e524c6fa3204ae298382d624741d0dc6638326e282c41be5e4254d8820772c5518a2c5a8c0c7f7eda19594a7eb539453e1ed7"
        actual = task.run().get().get(task.pk)

        self.assertEqual(expected, actual)

class IdentifyFileFormatTestCase(TestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.IdentifyFileFormat"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

        self.fname = os.path.join(self.datadir, "file1.txt")

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_file_with_content(self):
        with open(self.fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname
            }
        )

        expected = "Plain Text File"
        actual = task.run().get().get(task.pk)

        self.assertEqual(expected, actual)

    def test_filename_with_non_english_characters(self):
        fname = os.path.join(self.datadir, u'åäö.txt')

        with open(fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': fname
            }
        )

        expected = "Plain Text File"
        actual = task.run().get().get(task.pk)

        self.assertEqual(expected, actual)

    def test_empty_file_with_filename_with_non_english_characters(self):
        fname = os.path.join(self.datadir, u'åäö.txt')

        open(fname, "a").close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': fname
            }
        )

        expected = "Plain Text File"
        actual = task.run().get().get(task.pk)

        self.assertEqual(expected, actual)

    def test_non_existent_file_extension(self):
        fname = os.path.join(self.datadir, 'foo.zxczxc')

        with open(fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': fname
            }
        )

        with self.assertRaises(ValueError):
            task.run().get().get(task.pk)

    def test_non_existent_file_extension_with_filename_with_non_english_characters(self):
        fname = os.path.join(self.datadir, 'åäö.zxczxc')

        with open(fname, "w") as f:
            f.write('foo')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': fname
            }
        )

        with self.assertRaises(ValueError):
            task.run().get().get(task.pk)
