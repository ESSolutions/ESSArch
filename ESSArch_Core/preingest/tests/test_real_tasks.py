"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Tools for Archive (ETA)
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

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from unittest import mock

from install.install_default_config_eta import installDefaultEventTypes

from ESSArch_Core.configuration.models import (
    Path,
)

from ESSArch_Core.ip.models import (
    InformationPackage,
)

from ESSArch_Core.WorkflowEngine.models import (
    ProcessTask,
)


def setUpModule():
    installDefaultEventTypes()


class test_tasks(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = os.path.dirname(os.path.realpath(__file__))
        cls.ingest_reception = os.path.join(cls.root, "ingest_reception")
        cls.ingest_work = os.path.join(cls.root, "ingest_workarea")
        cls.gate_reception = os.path.join(cls.root, "gate_reception")

        for path in [cls.ingest_reception, cls.ingest_work, cls.gate_reception]:
            try:
                os.makedirs(path)
            except OSError as e:
                if e.errno != 17:
                    raise

        Path.objects.create(
            entity="path_ingest_reception",
            value=cls.ingest_reception
        )
        Path.objects.create(
            entity="ingest_workarea",
            value=cls.ingest_work
        )
        Path.objects.create(
            entity="path_gate_reception",
            value=cls.gate_reception
        )

    @classmethod
    def tearDownClass(cls):
        for path in [cls.ingest_reception, cls.ingest_work, cls.gate_reception]:
            try:
                shutil.rmtree(path)
            except BaseException:
                pass

        super(test_tasks, cls).tearDownClass()

    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

    @mock.patch('preingest.tasks.parse_submit_description')
    def test_receive_sip(self, mock_parse):
        srctar = os.path.join(self.ingest_reception, "foo.tar")
        srcxml = os.path.join(self.ingest_reception, "foo.xml")
        open(srctar, "a").close()
        open(srcxml, "a").close()

        mock_parse.configure_mock(**{'return_value': {
            'label': '1', 'object_path': srctar,
            'object_size': os.stat(srctar).st_size,
            'create_date': timezone.now()
        }})

        task = ProcessTask.objects.create(
            name="preingest.tasks.ReceiveSIP",
            args=[srcxml, srctar],
        )
        ip = InformationPackage.objects.get(pk=task.run().get())

        self.assertEqual(ip.object_path, srctar)
        self.assertEqual(ip.object_size, os.stat(srctar).st_size)

        self.assertTrue(os.path.isfile(os.path.join(self.ingest_work, ip.object_identifier_value + ".tar")))
        self.assertTrue(os.path.isfile(os.path.join(self.ingest_work, ip.object_identifier_value + ".xml")))

        task.undo()

        self.assertFalse(os.path.isfile(os.path.join(self.ingest_work, ip.object_identifier_value + ".tar")))
        self.assertFalse(os.path.isfile(os.path.join(self.ingest_work, ip.object_identifier_value + ".xml")))

        with self.assertRaises(InformationPackage.DoesNotExist):
            ip.refresh_from_db()

    def test_transfer_sip(self):
        ip = InformationPackage.objects.create()

        srctar = os.path.join(self.ingest_reception, "%s.tar" % ip.pk)
        srcxml = os.path.join(self.ingest_reception, "%s.xml" % ip.pk)
        open(srctar, "a").close()
        open(srcxml, "a").close()

        ip.object_path = os.path.join(self.ingest_reception, str(ip.pk) + ".tar")
        ip.save()

        task = ProcessTask.objects.create(
            name="preingest.tasks.TransferSIP",
            params={
                "ip": ip.pk
            },
        )
        task.run()

        self.assertTrue(os.path.isfile(os.path.join(self.gate_reception, str(ip.pk) + ".tar")))
        self.assertTrue(os.path.isfile(os.path.join(self.gate_reception, str(ip.pk) + ".xml")))

        task.undo()

        self.assertFalse(os.path.isfile(os.path.join(self.gate_reception, str(ip.pk) + ".tar")))
        self.assertFalse(os.path.isfile(os.path.join(self.gate_reception, str(ip.pk) + ".xml")))
