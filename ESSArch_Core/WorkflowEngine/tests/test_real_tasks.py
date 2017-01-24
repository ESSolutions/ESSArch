# -*- coding: utf-8 -*-

import os
import shutil
import string
import traceback

from celery import states as celery_states

from lxml import etree

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from ESSArch_Core.configuration.models import (
    EventType,
    Path
)

from ESSArch_Core.ip.models import (
    EventIP,
    InformationPackage,
)

from ESSArch_Core.util import find_and_replace_in_file

from ESSArch_Core.WorkflowEngine.models import (
    ProcessStep,
    ProcessTask,
)


def setUpModule():
    settings.CELERY_ALWAYS_EAGER = True
    settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True


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


class GenerateXMLTestCase(TestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.GenerateXML"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.xml')
        self.spec = {
            '-name': 'foo',
            '-attr': [
                {
                    '-name': 'fooAttr',
                    '#content': [{'var': 'foo'}]
                }
            ],
            '-children': [
                {
                    '-name': 'bar',
                    '#content': [{'var': 'bar'}]
                },
                {
                    '-name': 'baz',
                    '-containsFiles': True,
                    '#content': [{'var': 'FName'}]
                }
            ]
        }

        self.specData = {
            'foo': 'foodata',
            'bar': 'bardata'
        }

        Path.objects.create(
            entity="path_mimetypes_definitionfile",
            value=os.path.join(self.root, "mime.types")
        )

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_without_file(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'info': self.specData,
                'filesToCreate': {
                    self.fname: self.spec
                }
            }
        )

        task.run()

        tree = etree.parse(self.fname)
        root = tree.getroot()

        self.assertEqual(root.get('fooAttr'), 'foodata')
        self.assertEqual(root.find('bar').text, 'bardata')
        self.assertNotIn('baz', root.attrib)

    def test_with_file(self):
        open(os.path.join(self.datadir, 'example.txt'), 'a').close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'info': self.specData,
                'filesToCreate': {
                    self.fname: self.spec
                },
                'folderToParse': self.datadir
            }
        )

        task.run()

        tree = etree.parse(self.fname)
        root = tree.getroot()

        self.assertEqual(root.get('fooAttr'), 'foodata')
        self.assertEqual(root.find('bar').text, 'bardata')
        self.assertEqual(root.find('baz').text, 'example.txt')

    def test_undo(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'info': self.specData,
                'filesToCreate': {
                    self.fname: self.spec
                }
            }
        )

        task.run()

        self.assertTrue(os.path.isfile(self.fname))

        task.undo()

        self.assertFalse(os.path.isfile(self.fname))

    def test_undo_multiple_created_files(self):
        extra_file = os.path.join(self.datadir, 'test2.xml')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'info': self.specData,
                'filesToCreate': {
                    self.fname: self.spec,
                    extra_file: self.spec
                }
            }
        )

        task.run()

        self.assertTrue(os.path.isfile(self.fname))
        self.assertTrue(os.path.isfile(extra_file))

        task.undo()

        self.assertFalse(os.path.isfile(self.fname))
        self.assertFalse(os.path.isfile(extra_file))

class InsertXMLTestCase(TestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.InsertXML"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.xml')

        self.spec = {
            '-name': 'inserted',
            '#content': [{'var': 'inserted_var'}]
        }

        Path.objects.create(
            entity="path_mimetypes_definitionfile",
            value=os.path.join(self.root, "mime.types")
        )

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

        root = etree.fromstring("""
            <root>
                <foo><nested><duplicate></duplicate></nested></foo>
                <bar><duplicate></duplicate></bar>
            </root>
        """)

        with open(self.fname, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_insert_empty_to_root(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'root',
                'spec': self.spec,
            }
        )

        with self.assertRaises(TypeError):
            task.run()

    def test_insert_non_empty_to_root(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'root',
                'spec': self.spec,
                'info': {'inserted_var': 'inserted data'}
            }
        )

        task.run()

        tree = etree.parse(self.fname)
        inserted = tree.find('.//inserted')

        self.assertIsNotNone(inserted)
        self.assertEqual(inserted.text, 'inserted data')

    def test_insert_to_element_with_children(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'foo',
                'spec': self.spec,
                'info': {'inserted_var': 'inserted data'}
            }
        )

        task.run()

        tree = etree.parse(self.fname)

        foo = tree.find('.//foo')
        nested = tree.find('.//nested')
        inserted = tree.find('.//inserted')

        self.assertLess(foo.index(nested), foo.index(inserted))

    def test_insert_at_index(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'foo',
                'spec': self.spec,
                'info': {'inserted_var': 'inserted data'},
                'index': 0
            }
        )

        task.run()

        tree = etree.parse(self.fname)

        foo = tree.find('.//foo')
        nested = tree.find('.//nested')
        inserted = tree.find('.//inserted')

        self.assertLess(foo.index(inserted), foo.index(nested))

    def test_insert_to_duplicate_element(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'duplicate',
                'spec': self.spec,
                'info': {'inserted_var': 'inserted data'},
            }
        )

        task.run()

        tree = etree.parse(self.fname)
        duplicates = tree.findall('.//duplicate')

        self.assertIsNotNone(duplicates[0].find('.//inserted'))
        self.assertIsNone(duplicates[1].find('.//inserted'))

    def test_undo(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'foo',
                'spec': self.spec,
                'info': {'inserted_var': 'inserted data'},
            }
        )

        task.run()

        tree = etree.parse(self.fname)
        self.assertIsNotNone(tree.find('.//inserted'))

        task.undo()

        tree = etree.parse(self.fname)
        self.assertIsNone(tree.find('.//inserted'))

    def test_undo_index(self):
        task1 = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'foo',
                'spec': self.spec,
                'info': {'inserted_var': 'inserted 1'},
            }
        )

        task2 = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'foo',
                'spec': self.spec,
                'info': {'inserted_var': 'inserted 2'},
                'index': 0
            }
        )

        task3 = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'elementToAppendTo': 'foo',
                'spec': self.spec,
                'info': {'inserted_var': 'inserted 3'},
                'index': 2
            }
        )

        task1.run()
        task2.run()
        task3.run()

        tree = etree.parse(self.fname)
        found = tree.findall('.//inserted')
        self.assertEqual(len(found), 3)
        self.assertEqual(found[0].text, 'inserted 2')
        self.assertEqual(found[1].text, 'inserted 3')
        self.assertEqual(found[2].text, 'inserted 1')

        task3.undo()

        tree = etree.parse(self.fname)
        found = tree.findall('.//inserted')
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0].text, 'inserted 2')
        self.assertEqual(found[1].text, 'inserted 1')

        task2.undo()

        tree = etree.parse(self.fname)
        found = tree.findall('.//inserted')
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].text, 'inserted 1')

        task1.undo()

        tree = etree.parse(self.fname)
        self.assertIsNone(tree.find('.//inserted'))


class AppendEventsTestCase(TestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.AppendEvents"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.xml')
        self.ip = InformationPackage.objects.create(Label="testip")
        self.user = User.objects.create(username="testuser")

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

        root = etree.fromstring("""
            <premis:premis xmlns:premis='http://xml.ra.se/PREMIS'
            xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'
            xmlns:xlink='http://www.w3.org/1999/xlink'
            xsi:schemaLocation='http://xml.ra.se/PREMIS http://xml.ra.se/PREMIS/ESS/RA_PREMIS_PreVersion.xsd'
            version='2.0'>
            </premis:premis>
        """)

        with open(self.fname, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_undo(self):
        event_type = EventType.objects.create()

        for i in range(10):
            EventIP.objects.create(
                eventType=event_type, linkingAgentIdentifierValue=self.user,
                linkingObjectIdentifierValue=self.ip
            ),

        task1 = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'events': EventIP.objects.all()
            },
            information_package=self.ip
        )

        task1.run()

        EventIP.objects.all().delete()

        for i in range(10):
            EventIP.objects.create(
                eventType=event_type, linkingAgentIdentifierValue=self.user,
                linkingObjectIdentifierValue=self.ip
            ),

        tree = etree.parse(self.fname)
        found = tree.findall('.//{*}event')
        self.assertEqual(len(found), 10)

        task2 = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'events': EventIP.objects.all()
            },
            information_package=self.ip
        )

        task2.run()

        tree = etree.parse(self.fname)
        found = tree.findall('.//{*}event')
        self.assertEqual(len(found), 20)

        task2.undo()

        tree = etree.parse(self.fname)
        found = tree.findall('.//{*}event')
        self.assertEqual(len(found), 10)

        task1.undo()

        tree = etree.parse(self.fname)
        found = tree.findall('.//{*}event')
        self.assertEqual(len(found), 0)

class ValidateFilesTestCase(TestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.ValidateFiles"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.xml')
        self.ip = InformationPackage.objects.create(Label="testip")
        self.user = User.objects.create(username="testuser")

        Path.objects.create(
            entity="path_mimetypes_definitionfile",
            value=os.path.join(self.root, "mime.types")
        )

        self.filesToCreate = {
            self.fname: {
                '-name': 'root',
                '-children': [{
                    '-name': 'object',
                    '-containsFiles': True,
                    '-filters': {'FName': '^((?!' + os.path.basename(self.fname) + ').)*$'},
                    '-children': [
                        {
                            '-name': 'storage',
                            '-children': [{
                                '-name': 'contentLocation',
                                '-children': [{
                                    '-name': 'contentLocationValue',
                                    '#content': [
                                        {
                                            'text': 'file:///',
                                        },
                                        {
                                            'var': 'href'
                                        }
                                    ]
                                }]
                            }]
                        },
                        {
                            '-name': 'objectCharacteristics',
                            '-children': [
                                {
                                    '-name': 'fixity',
                                    '-children': [
                                        {
                                            '-name': 'messageDigest',
                                            '#content': [{
                                                'var': 'FChecksum'
                                            }]
                                        },
                                        {
                                            '-name': 'messageDigestAlgorithm',
                                            '#content': [{
                                                'var': 'FChecksumType'
                                            }]
                                        }
                                    ]
                                },
                                {
                                    '-name': 'format',
                                    '-children': [
                                        {
                                            '-name': 'formatDesignation',
                                            '-children': [
                                                {
                                                    '-name': 'formatName',
                                                    '#content': [
                                                        {
                                                            'var': 'FFormatName'
                                                        }
                                                    ]
                                                }
                                            ]
                                        },
                                        {
                                            '-name': 'messageDigestAlgorithm',
                                            '#content': [{
                                                'var': 'FChecksumType'
                                            }]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }]
            }
        }

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

        root = etree.fromstring('<root></root>')

        with open(self.fname, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_no_validation(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'validate_fileformat': False,
                'validate_integrity': False,
            }
        )

        res = task.run().get().get(task.pk)

        self.assertEqual(len(res), 0)

    def test_validation_without_files(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip,
                'xmlfile': self.fname
            }
        )

        res = task.run().get().get(task.pk)

        self.assertEqual(len(res), 0)

    def test_validation_with_files(self):
        num_of_files = 3

        for i in range(num_of_files):
            with open(os.path.join(self.datadir, '%s.txt' % i), 'w') as f:
                f.write('%s' % i)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip,
                'xmlfile': self.fname,
                'rootdir': self.datadir
            }
        )

        res = task.run().get().get(task.pk)

        self.assertTrue(len(res) >= num_of_files)

    def test_change_checksum(self):
        num_of_files = 3

        for i in range(num_of_files):
            with open(os.path.join(self.datadir, '%s.txt' % i), 'w') as f:
                f.write('%s' % i)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip,
                'xmlfile': self.fname,
                'rootdir': self.datadir
            }
        )

        task.run()

        for i in range(num_of_files):
            with open(os.path.join(self.datadir, '%s.txt' % i), 'w') as f:
                f.write('%s updated' % i)

        with self.assertRaisesRegexp(AssertionError, 'checksum'):
            task.run()

    def test_change_file_format(self):
        num_of_files = 3

        for i in range(num_of_files):
            with open(os.path.join(self.datadir, '%s.txt' % i), 'w') as f:
                f.write('%s' % i)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip,
                'xmlfile': self.fname,
                'rootdir': self.datadir
            }
        )

        task.run()

        for i in range(num_of_files):
            src = os.path.join(self.datadir, '%s.txt' % i)
            dst = os.path.join(self.datadir, '%s.pdf' % i)

            shutil.move(src, dst)

        find_and_replace_in_file(self.fname, '.txt', '.pdf')

        with self.assertRaisesRegexp(AssertionError, 'fileformat'):
            task.run()

    def test_fail_and_stop_step_when_inner_task_fails(self):
        fname = os.path.join(self.datadir, 'test1.txt')
        open(fname, 'a').close()

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        with open(fname, 'w') as f:
            f.write('added')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip,
                'xmlfile': self.fname,
                'rootdir': self.datadir
            }
        )

        with self.assertRaises(AssertionError):
            task.run_eagerly()

        step = ProcessStep.objects.get(name="Validate Files")

        self.assertEqual(task.status, celery_states.FAILURE)
        self.assertEqual(step.status, celery_states.FAILURE)


class ValidateIntegrityTestCase(TestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.ValidateIntegrity"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.txt')

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_correct(self):
        open(self.fname, 'a').close()

        t = ProcessTask.objects.create(
            name='ESSArch_Core.tasks.CalculateChecksum',
            params={
                'filename': self.fname
            }
        )

        checksum = t.run().get().get(t.pk)

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'checksum': checksum,
            }
        )

        task.run()

    def test_incorrect(self):
        open(self.fname, 'a').close()

        t = ProcessTask.objects.create(
            name='ESSArch_Core.tasks.CalculateChecksum',
            params={
                'filename': self.fname
            }
        )

        checksum = t.run().get().get(t.pk)

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'checksum': checksum,
            }
        )

        with open(self.fname, 'w') as f:
            f.write('foo')

        with self.assertRaisesRegexp(AssertionError, 'checksum'):
            task.run()


class ValidateFileFormatTestCase(TestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.ValidateFileFormat"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.txt')

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_correct(self):
        open(self.fname, 'a').close()

        t = ProcessTask.objects.create(
            name='ESSArch_Core.tasks.IdentifyFileFormat',
            params={
                'filename': self.fname
            }
        )

        fformat = t.run().get().get(t.pk)

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': self.fname,
                'fileformat': fformat,
            }
        )

        task.run()

    def test_incorrect(self):
        open(self.fname, 'a').close()

        t = ProcessTask.objects.create(
            name='ESSArch_Core.tasks.IdentifyFileFormat',
            params={
                'filename': self.fname
            }
        )

        fformat = t.run().get().get(t.pk)

        newfile = string.replace(self.fname, '.txt', '.pdf')
        shutil.move(self.fname, newfile)

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'filename': newfile,
                'fileformat': fformat,
            }
        )

        with self.assertRaisesRegexp(AssertionError, 'format'):
            task.run()


class ValidateXMLFileTestCase(TestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.ValidateXMLFile"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.xml')
        self.schema = os.path.join(self.datadir, 'test1.xsd')

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

        schema_root = etree.fromstring("""
            <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                <xsd:element name="foo" type="xsd:integer"/>
            </xsd:schema>
        """)

        with open(self.schema, 'w') as f:
            f.write(etree.tostring(schema_root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_correct(self):
        root = etree.fromstring('<foo>5</foo>')

        with open(self.fname, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'xml_filename': self.fname,
                'schema_filename': self.schema
            }
        )

        task.run()

    def test_incorrect(self):
        root = etree.fromstring('<foo>bar</foo>')

        with open(self.fname, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'xml_filename': self.fname,
                'schema_filename': self.schema
            }
        )

        with self.assertRaisesRegexp(etree.DocumentInvalid, 'not a valid value of the atomic type'):
            task.run()


class ValidateLogicalPhysicalRepresentationTestCase(TestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.ValidateLogicalPhysicalRepresentation"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")
        self.fname = os.path.join(self.datadir, 'test1.xml')
        self.ip = InformationPackage.objects.create(Label="testip")
        self.user = User.objects.create(username="testuser")

        Path.objects.create(
            entity="path_mimetypes_definitionfile",
            value=os.path.join(self.root, "mime.types")
        )

        self.filesToCreate = {
            self.fname: {
                '-name': 'root',
                '-children': [{
                    '-name': 'object',
                    '-containsFiles': True,
                    '-filters': {'FName': '^((?!' + os.path.basename(self.fname) + ').)*$'},
                    '-children': [
                        {
                            '-name': 'storage',
                            '-children': [{
                                '-name': 'contentLocation',
                                '-children': [{
                                    '-name': 'contentLocationValue',
                                    '#content': [
                                        {
                                            'text': 'file:///',
                                        },
                                        {
                                            'var': 'href'
                                        }
                                    ]
                                }]
                            }]
                        }
                    ]
                }]
            }
        }

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

        root = etree.fromstring('<root></root>')

        with open(self.fname, 'w') as f:
            f.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_validation_without_files(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'xmlfile': self.fname
            }
        )

        task.run()

    def test_validation_with_files(self):
        num_of_files = 3
        files = []

        for i in range(num_of_files):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('%s' % i)
            files.append(fname)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'files': files,
                'files_reldir': self.datadir,
                'xmlfile': self.fname,
            }
        )

        task.run()

    def test_validation_with_incorrect_file_name(self):
        num_of_files = 3
        files = []

        for i in range(num_of_files):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('%s' % i)
            files.append(fname)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        files[0] = string.replace(files[0], 'txt', 'txtx')

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'files': files,
                'files_reldir': self.datadir,
                'xmlfile': self.fname,
            }
        )

        with self.assertRaisesRegexp(AssertionError, "the logical representation differs from the physical"):
            task.run()

    def test_validation_with_too_many_files(self):
        num_of_files = 3
        files = []

        for i in range(num_of_files):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('%s' % i)
            files.append(fname)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        fname = os.path.join(self.datadir, '%s.txt' % (num_of_files+1))
        files.append(fname)

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'files': files,
                'files_reldir': self.datadir,
                'xmlfile': self.fname,
            }
        )

        with self.assertRaisesRegexp(AssertionError, "the logical representation differs from the physical"):
            task.run()

    def test_validation_with_too_few_files(self):
        num_of_files = 3
        files = []

        for i in range(num_of_files):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('%s' % i)
            files.append(fname)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        fname = os.path.join(self.datadir, '%s.txt' % (num_of_files+1))
        files.pop()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'files': files,
                'files_reldir': self.datadir,
                'xmlfile': self.fname,
            }
        )

        with self.assertRaisesRegexp(AssertionError, "the logical representation differs from the physical"):
            task.run()

    def test_validation_with_file_in_wrong_folder(self):
        num_of_files = 3
        files = []

        for i in range(num_of_files):
            fname = os.path.join(self.datadir, '%s.txt' % i)
            with open(fname, 'w') as f:
                f.write('%s' % i)
            files.append(fname)

        ProcessTask.objects.create(
            name='ESSArch_Core.tasks.GenerateXML',
            params={
                'filesToCreate': self.filesToCreate,
                'folderToParse': self.datadir
            }
        ).run()

        moved_file = files[0]
        new_dir = os.path.join(self.datadir, 'new_dir')
        new_file = os.path.join(new_dir, os.path.basename(moved_file))

        os.mkdir(new_dir)
        shutil.move(moved_file, new_file)

        files[0] = new_file

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'files': files,
                'files_reldir': self.datadir,
                'xmlfile': self.fname,
            }
        )

        with self.assertRaisesRegexp(AssertionError, "the logical representation differs from the physical"):
            task.run()


class UpdateIPStatusTestCase(TestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.UpdateIPStatus"
        self.ip = InformationPackage.objects.create(Label="testip", State='initial')

    def test_update(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip,
                'status': 'new'
            }
        )

        task.run()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.State, 'new')

    def test_undo(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip,
                'status': 'new'
            }
        )

        task.run()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.State, 'new')

        task.undo()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.State, 'initial')


class UpdateIPPathTestCase(TestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.UpdateIPPath"
        self.ip = InformationPackage.objects.create(Label="testip", ObjectPath='initial')

    def test_update(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip,
                'path': 'new'
            }
        )

        task.run()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.ObjectPath, 'new')

    def test_undo(self):
        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'ip': self.ip,
                'path': 'new'
            }
        )

        task.run()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.ObjectPath, 'new')

        task.undo()

        self.ip.refresh_from_db()
        self.assertEqual(self.ip.ObjectPath, 'initial')


class DeleteFilesTestCase(TestCase):
    def setUp(self):
        self.taskname = "ESSArch_Core.tasks.DeleteFiles"
        self.root = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.root, "datadir")

        try:
            os.mkdir(self.datadir)
        except OSError as e:
            if e.errno != 17:
                raise

    def tearDown(self):
        shutil.rmtree(self.datadir)

    def test_delete_empty_dir(self):
        dirname = os.path.join(self.datadir, 'newdir')
        os.mkdir(dirname)

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'path': dirname
            }
        )

        task.run()

        self.assertFalse(os.path.isdir(dirname))

    def test_delete_dir_with_files(self):
        dirname = os.path.join(self.datadir, 'newdir')
        os.mkdir(dirname)

        for i in range(3):
            open(os.path.join(dirname, str(i)), 'a').close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'path': dirname
            }
        )

        task.run()

        self.assertFalse(os.path.isdir(dirname))

    def test_delete_file(self):
        fname = os.path.join(self.datadir, 'test.txt')
        open(fname, 'a').close()

        task = ProcessTask.objects.create(
            name=self.taskname,
            params={
                'path': fname
            }
        )

        task.run()

        self.assertFalse(os.path.isfile(fname))
