"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Core
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import os
import shutil
import tempfile

import unittest.mock
import six
from django.test import TestCase
from lxml import etree

from ESSArch_Core.essxml.util import (find_file, find_files, get_agent,
                                      get_altrecordid, get_altrecordids,
                                      get_objectpath, parse_reference_code,
                                      parse_submit_description)


class FindFilesTestCase(TestCase):
    def setUp(self):
        self.bd = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.bd)

        self.datadir = os.path.join(self.bd, "datafiles")
        os.mkdir(self.datadir)

    def test_empty(self):
        xmlfile = os.path.join(self.datadir, "test.xml")

        with open(xmlfile, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root xmlns:xlink="http://www.w3.org/1999/xlink"></root>
            ''')

        expected = []
        found = find_files(xmlfile, rootdir=self.datadir)
        self.assertEqual(len(found), len(expected))

    def test_files_file_element(self):
        xmlfile = os.path.join(self.datadir, "test.xml")

        with open(xmlfile, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root xmlns:xlink="http://www.w3.org/1999/xlink">
                <file><FLocat href="file:///1.txt"/></file>
                <file><FLocat href="file:2.txt"/></file>
                <file><FLocat href="3.txt"/></file>
                <file><FLocat xlink:href="4.txt"/></file>
            </root>
            ''')

        expected = ['1.txt', '2.txt', '3.txt', '4.txt']
        found = find_files(xmlfile, rootdir=self.datadir)
        six.assertCountEqual(self, [x.path for x in found], expected)

    def test_files_mdRef_element(self):
        xmlfile = os.path.join(self.datadir, "test.xml")

        with open(xmlfile, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root xmlns:xlink="http://www.w3.org/1999/xlink">
                <mdRef href="file:///1.txt"/>
                <mdRef href="2.txt"/>
            </root>
            ''')

        expected = ['1.txt', '2.txt']
        found = find_files(xmlfile, rootdir=self.datadir)
        self.assertEqual(len(found), len(expected))

    def test_files_object_element(self):
        xmlfile = os.path.join(self.datadir, "test.xml")

        with open(xmlfile, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root xmlns:xlink="http://www.w3.org/1999/xlink">
                <object>
                    <storage>
                        <contentLocation>
                            <contentLocationValue>file:///1.txt</contentLocationValue>
                        </contentLocation>
                    </storage>
                </object>
                <object>
                    <storage>
                        <contentLocation>
                            <contentLocationValue>file:///2.txt</contentLocationValue>
                        </contentLocation>
                    </storage>
                </object>
            </root>
            ''')

        expected = ['1.txt', '2.txt']
        found = find_files(xmlfile, rootdir=self.datadir)
        self.assertEqual(len(found), len(expected))

    def test_pointer(self):
        xmlfile = os.path.join(self.datadir, "test.xml")
        ext1 = os.path.join(self.datadir, "ext1.xml")
        ext2 = os.path.join(self.datadir, "ext2.xml")

        with open(xmlfile, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root xmlns:xlink="http://www.w3.org/1999/xlink">
                <mptr xlink:href="ext1.xml"/>
                <mptr xlink:href="ext2.xml"/>
            </root>
            ''')

        with open(ext1, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root xmlns:xlink="http://www.w3.org/1999/xlink">
                <file><FLocat href="1.txt"/></file>
                <file><FLocat href="2.txt"/></file>
            </root>
            ''')

        with open(ext2, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root xmlns:xlink="http://www.w3.org/1999/xlink">
                <file><FLocat href="1.pdf"/></file>
                <file><FLocat href="2.pdf"/></file>
            </root>
            ''')

        expected = ['ext1.xml', 'ext2.xml', '1.txt', '1.pdf', '2.txt', '2.pdf']
        found = find_files(xmlfile, rootdir=self.datadir)
        self.assertEqual(len(found), len(expected))
        six.assertCountEqual(self, found, expected)


class FindFileTestCase(TestCase):
    def setUp(self):
        self.bd = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.bd)

        self.datadir = os.path.join(self.bd, "datafiles")
        os.mkdir(self.datadir)

    def test_files_file_element(self):
        xmlfile = os.path.join(self.datadir, "test.xml")

        with open(xmlfile, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root xmlns:xlink="http://www.w3.org/1999/xlink">
                <file><FLocat href="file:///1.txt"/></file>
                <file><FLocat href="file:2.txt"/></file>
                <file><FLocat href="3.txt"/></file>
            </root>
            ''')

        found = find_file('1.txt', xmlfile=xmlfile, rootdir=self.datadir)
        self.assertIsNotNone(found)

        found = find_file('2.txt', xmlfile=xmlfile, rootdir=self.datadir)
        self.assertIsNotNone(found)

        found = find_file('4.txt', xmlfile=xmlfile, rootdir=self.datadir)
        self.assertIsNone(found)

    def test_files_object_element(self):
        xmlfile = os.path.join(self.datadir, "test.xml")

        with open(xmlfile, 'w') as xml:
            xml.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <root xmlns:xlink="http://www.w3.org/1999/xlink">
                <object>
                    <storage>
                        <contentLocation>
                            <contentLocationValue>file:///1.txt</contentLocationValue>
                        </contentLocation>
                    </storage>
                </object>
                <object>
                    <storage>
                        <contentLocation>
                            <contentLocationValue>file:///2.txt</contentLocationValue>
                        </contentLocation>
                    </storage>
                </object>
            </root>
            ''')

        found = find_file('1.txt', xmlfile=xmlfile, rootdir=self.datadir)
        self.assertIsNotNone(found)

        found = find_file('2.txt', xmlfile=xmlfile, rootdir=self.datadir)
        self.assertIsNotNone(found)

        found = find_file('3.txt', xmlfile=xmlfile, rootdir=self.datadir)
        self.assertIsNone(found)


class GetAltrecordidTestCase(TestCase):
    def test_existing(self):
        el = etree.fromstring('''
            <root>
                <altRecordID TYPE="foo">bar</altRecordID>
            </root>
        ''')

        self.assertEqual(get_altrecordid(el, 'foo'), ['bar'])

    def test_multiple_results(self):
        el = etree.fromstring('''
            <root>
                <altRecordID TYPE="foo">first</altRecordID>
                <altRecordID TYPE="foo">second</altRecordID>
            </root>
        ''')

        self.assertEqual(get_altrecordid(el, 'foo'), ['first', 'second'])

    def test_non_existing_type(self):
        el = etree.fromstring('''
            <root>
                <altRecordID TYPE="foo">bar</altRecordID>
            </root>
        ''')

        self.assertEqual(get_altrecordid(el, 'bar'), [])

    def test_non_existing_element(self):
        el = etree.fromstring('''
            <root></root>
        ''')

        self.assertEqual(get_altrecordid(el, 'bar'), [])


class GetAltrecordidsTestCase(TestCase):
    def test_none(self):
        el = etree.fromstring('''
            <root></root>
        ''')

        self.assertEqual(get_altrecordids(el), {})

    def test_single(self):
        el = etree.fromstring('''
            <root>
                <altRecordID TYPE="foo">bar</altRecordID>
            </root>
        ''')

        self.assertEqual(get_altrecordids(el), {'foo': ['bar']})

    def test_multiple(self):
        el = etree.fromstring('''
            <root>
                <altRecordID TYPE="foo">bar</altRecordID>
                <altRecordID TYPE="bar">foo</altRecordID>
            </root>
        ''')

        self.assertEqual(get_altrecordids(el), {'foo': ['bar'], 'bar': ['foo']})

    def test_multiple_same_type(self):
        el = etree.fromstring('''
            <root>
                <altRecordID TYPE="foo">first</altRecordID>
                <altRecordID TYPE="foo">second</altRecordID>
            </root>
        ''')

        self.assertEqual(get_altrecordids(el), {'foo': ['first', 'second']})


class GetAgentTestCase(TestCase):
    def test_existing_role(self):
        el = etree.fromstring('''
            <root>
                <agent ROLE="foo">
                    <name>foo_name</name>
                    <note>foo_note</note>
                </agent>
            </root>
        ''')

        self.assertEqual(get_agent(el, ROLE='foo'), {'name': 'foo_name', 'notes': ['foo_note']})

    def test_existing_otherrole(self):
        el = etree.fromstring('''
            <root>
                <agent OTHERROLE="foo">
                    <name>foo_name</name>
                    <note>foo_note</note>
                </agent>
            </root>
        ''')

        self.assertEqual(get_agent(el, OTHERROLE='foo'), {'name': 'foo_name', 'notes': ['foo_note']})

    def test_existing_type(self):
        el = etree.fromstring('''
            <root>
                <agent TYPE="foo">
                    <name>foo_name</name>
                    <note>foo_note</note>
                </agent>
            </root>
        ''')

        self.assertEqual(get_agent(el, TYPE='foo'), {'name': 'foo_name', 'notes': ['foo_note']})

    def test_existing_othertype(self):
        el = etree.fromstring('''
            <root>
                <agent OTHERTYPE="foo">
                    <name>foo_name</name>
                    <note>foo_note</note>
                </agent>
            </root>
        ''')

        self.assertEqual(get_agent(el, OTHERTYPE='foo'), {'name': 'foo_name', 'notes': ['foo_note']})

    def test_multiple_agents(self):
        el = etree.fromstring('''
            <root>
                <agent ROLE="foo">
                    <name>foo_name</name>
                    <note>foo_note</note>
                </agent>
                <agent ROLE="bar">
                    <name>bar_name</name>
                    <note>bar_note</note>
                </agent>
            </root>
        ''')

        self.assertEqual(get_agent(el, ROLE='foo'), {'name': 'foo_name', 'notes': ['foo_note']})
        self.assertEqual(get_agent(el, ROLE='bar'), {'name': 'bar_name', 'notes': ['bar_note']})

    def test_non_existing_element(self):
        el = etree.fromstring('''
            <root></root>
        ''')

        with self.assertRaises(IndexError):
            get_agent(el)


class GetObjectPathTestCase(TestCase):
    def test_no_prefix(self):
        el = etree.fromstring('''
            <root>
                <FLocat href="foo"></FLocat>
            </root>
        ''')

        self.assertEqual(get_objectpath(el), 'foo')

    def test_prefix(self):
        el = etree.fromstring('''
            <root>
                <FLocat href="file:///foo"></FLocat>
            </root>
        ''')

        self.assertEqual(get_objectpath(el), 'foo')


class ParseReferenceCodeTestCase(TestCase):
    def test_single_node(self):
        tree = parse_reference_code('foo')
        self.assertEqual(tree, ['foo'])

    def test_single_node_leading_slash(self):
        tree = parse_reference_code('/foo')
        self.assertEqual(tree, ['foo'])

    def test_single_node_trailing_slash(self):
        tree = parse_reference_code('foo/')
        self.assertEqual(tree, ['foo'])

    def test_multiple_nodes(self):
        tree = parse_reference_code('foo/bar/baz')
        self.assertEqual(tree, ['foo', 'bar', 'baz'])

    def test_multiple_nodes_same_name(self):
        tree = parse_reference_code('foo/bar/foo')
        self.assertEqual(tree, ['foo', 'bar', 'foo'])


class ParseSubmitDescriptionTestCase(TestCase):
    def setUp(self):
        self.xmlfile = tempfile.NamedTemporaryFile(delete=False)

    def tearDown(self):
        os.remove(self.xmlfile.name)

    def test_objid_and_create_date(self):
        self.xmlfile.write(b'''
            <mets OBJID="123">
                <metsHdr CREATEDATE="456"></metsHdr>
            </mets>
        ''')
        self.xmlfile.close()
        ip = parse_submit_description(self.xmlfile.name)

        self.assertEqual(ip['id'], '123')
        self.assertEqual(ip['create_date'], '456')

    def test_objid_with_prefix(self):
        self.xmlfile.write(b'''
            <mets OBJID="ID:123">
                <metsHdr CREATEDATE="456"></metsHdr>
            </mets>
        ''')
        self.xmlfile.close()
        ip = parse_submit_description(self.xmlfile.name)
        self.assertEqual(ip['id'], '123')

    def test_no_objid(self):
        self.xmlfile.write(b'''
            <mets>
                <metsHdr CREATEDATE="456"></metsHdr>
            </mets>
        ''')
        self.xmlfile.close()
        ip = parse_submit_description(self.xmlfile.name)
        self.assertEqual(ip['id'], os.path.splitext(os.path.basename(self.xmlfile.name))[0])

    @mock.patch('ESSArch_Core.essxml.util.os.stat')
    @mock.patch('ESSArch_Core.essxml.util.get_objectpath')
    def test_objpath(self, mock_objectpath, mock_os_stat):
        mock_objectpath.return_value = 'foo'
        mock_os_stat.return_value = mock.Mock(**{'st_size': 24})

        self.xmlfile.write(b'''
            <mets OBJID="123">
                <metsHdr CREATEDATE="456"></metsHdr>
            </mets>
        ''')
        self.xmlfile.close()
        ip = parse_submit_description(self.xmlfile.name)

        self.assertEqual(ip['id'], '123')
        self.assertEqual(ip['create_date'], '456')
        self.assertEqual(ip['object_path'], 'foo')
        self.assertEqual(ip['object_size'], 24)

    def test_information_class_in_root(self):
        self.xmlfile.write(b'''
            <mets INFORMATIONCLASS="123">
                <metsHdr CREATEDATE="456"></metsHdr>
            </mets>
        ''')
        self.xmlfile.close()
        ip = parse_submit_description(self.xmlfile.name)
        self.assertEqual(ip['information_class'], 123)

    def test_information_class_in_altrecordid(self):
        self.xmlfile.write(b'''
            <mets>
                <metsHdr CREATEDATE="456"></metsHdr>
                <altRecordID TYPE="INFORMATIONCLASS">123</altRecordID>
            </mets>
        ''')
        self.xmlfile.close()
        ip = parse_submit_description(self.xmlfile.name)
        self.assertEqual(ip['information_class'], 123)

    def test_information_class_in_root_and_altrecordid(self):
        self.xmlfile.write(b'''
            <mets INFORMATIONCLASS="123">
                <metsHdr CREATEDATE="456"></metsHdr>
                <altRecordID TYPE="INFORMATIONCLASS">456</altRecordID>
            </mets>
        ''')
        self.xmlfile.close()
        ip = parse_submit_description(self.xmlfile.name)
        self.assertEqual(ip['information_class'], 123)

    def test_information_class_with_letters(self):
        self.xmlfile.write(b'''
            <mets INFORMATIONCLASS="class 123">
                <metsHdr CREATEDATE="456"></metsHdr>
            </mets>
        ''')
        self.xmlfile.close()
        ip = parse_submit_description(self.xmlfile.name)
        self.assertEqual(ip['information_class'], 123)

    def test_information_class_with_multiple_numbers(self):
        self.xmlfile.write(b'''
            <mets INFORMATIONCLASS="123 456">
                <metsHdr CREATEDATE="456"></metsHdr>
            </mets>
        ''')
        self.xmlfile.close()
        ip = parse_submit_description(self.xmlfile.name)
        self.assertEqual(ip['information_class'], 123)
