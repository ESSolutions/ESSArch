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

from django.test import TestCase

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.util import timestamp_to_datetime


class InformationPackageTestCase(TestCase):
    def setUp(self):
        self.bd = os.path.dirname(os.path.realpath(__file__))
        Path.objects.create(
            entity="path_mimetypes_definitionfile",
            value=os.path.join(self.bd, "mime.types")
        )

        self.datadir = tempfile.mkdtemp()
        self.ip = InformationPackage.objects.create(object_path=self.datadir)

    def tearDown(self):
        try:
            shutil.rmtree(self.datadir)
        except:
            pass

    def test_list_file(self):
        _, path = tempfile.mkstemp(dir=self.datadir)
        self.assertEqual(self.ip.files().data, [{'type': 'file', 'name': os.path.basename(path), 'size': 0, 'modified': timestamp_to_datetime(os.stat(path).st_mtime)}])

    def test_list_folder(self):
        path = tempfile.mkdtemp(dir=self.datadir)
        self.assertEqual(self.ip.files().data, [{'type': 'dir', 'name': os.path.basename(path), 'size': 0, 'modified': timestamp_to_datetime(os.stat(path).st_mtime)}])

    def test_list_folder_content(self):
        path = tempfile.mkdtemp(dir=self.datadir)
        _, filepath = tempfile.mkstemp(dir=path)
        self.assertEqual(self.ip.files(path=path).data, [{'type': 'file', 'name': os.path.basename(filepath), 'size': os.stat(filepath).st_size, 'modified': timestamp_to_datetime(os.stat(filepath).st_mtime)}])
