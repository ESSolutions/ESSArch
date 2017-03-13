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
from collections import OrderedDict

from django.test import TestCase

from lxml import etree

from ESSArch_Core.essxml.Generator.xmlGenerator import XMLGenerator, parseContent

from ESSArch_Core.configuration.models import (
    Path,
)
from ESSArch_Core.essxml.util import find_files
from ESSArch_Core.WorkflowEngine.models import ProcessTask


class FindFilesTestCase(TestCase):
    def setUp(self):
        self.bd = os.path.dirname(os.path.realpath(__file__))
        self.datadir = os.path.join(self.bd, "datafiles")
        os.mkdir(self.datadir)

    def tearDown(self):
        try:
            shutil.rmtree(self.datadir)
        except:
            pass

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
        self.assertItemsEqual(found, expected)
