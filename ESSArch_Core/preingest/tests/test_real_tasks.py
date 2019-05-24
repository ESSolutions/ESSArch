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
from django.contrib.auth.models import User
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from unittest import mock

from ESSArch_Core.install.install_default_config import installDefaultEventTypes

from ESSArch_Core.configuration.models import (
    EventType, Path,
)

from ESSArch_Core.ip.models import (
    EventIP, InformationPackage,
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


class test_tasks_etp(TransactionTestCase):
    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

        self.root = os.path.dirname(os.path.realpath(__file__))
        self.prepare_path = os.path.join(self.root, "prepare")
        self.preingest_reception = os.path.join(self.root, "preingest_reception")
        self.ingest_reception = os.path.join(self.root, "ingest_reception")

        for path in [self.prepare_path, self.preingest_reception, self.ingest_reception]:
            try:
                os.makedirs(path)
            except OSError as e:
                if e.errno != 17:
                    raise

        Path.objects.create(
            entity="path_preingest_prepare",
            value=self.prepare_path
        )
        Path.objects.create(
            entity="path_preingest_reception",
            value=self.preingest_reception
        )
        Path.objects.create(
            entity="path_ingest_reception",
            value=self.ingest_reception
        )

    def tearDown(self):
        for path in [self.prepare_path, self.preingest_reception, self.ingest_reception]:
            try:
                shutil.rmtree(path)
            except BaseException:
                pass

    def test_prepare_ip(self):
        label = "ip1"
        user = User.objects.create(username="user1")
        event_type = EventType.objects.create(eventType=10100)

        task = ProcessTask.objects.create(
            name="preingest.tasks.PrepareIP",
            params={
                "label": label,
                "responsible": str(user.pk)
            },
            responsible=user
        )
        task.run()

        ip = InformationPackage.objects.filter(label=label).first()

        self.assertIsNotNone(ip)

        self.assertTrue(
            EventIP.objects.filter(
                linkingObjectIdentifierValue=ip,
                eventOutcome=0,
                linkingAgentIdentifierValue=user,
                eventType=event_type,
            ).exists()
        )

        task.undo()

        self.assertFalse(
            InformationPackage.objects.filter(label=label).exists()
        )

    def test_create_ip_root_dir(self):
        ip = InformationPackage.objects.create(label="ip1")
        user = User.objects.create(username="user1")
        prepare_path = Path.objects.get(entity="path_preingest_prepare").value
        prepare_path = os.path.join(prepare_path, str(ip.pk))
        event_type = EventType.objects.create(eventType=10110)

        task = ProcessTask.objects.create(
            name="preingest.tasks.CreateIPRootDir",
            params={
                "information_package": ip.pk,
            },
            responsible=user
        )
        task.run()

        self.assertTrue(
            os.path.isdir(prepare_path)
        )

        self.assertTrue(
            EventIP.objects.filter(
                linkingObjectIdentifierValue=ip,
                eventOutcome=0,
                linkingAgentIdentifierValue=user,
                eventType=event_type,
            ).exists()
        )

        task.undo()

        self.assertFalse(
            os.path.isdir(prepare_path)
        )

    def test_create_physical_model(self):
        ip = InformationPackage.objects.create(label="ip1")
        prepare_path = Path.objects.get(entity="path_preingest_prepare").value
        path = os.path.join(prepare_path, str(ip.pk))

        task = ProcessTask.objects.create(
            name="preingest.tasks.CreatePhysicalModel",
            params={
                "structure": [
                    {
                        "name": "dir1",
                        "type": "folder"
                    },
                    {
                        "name": "dir2",
                        "type": "folder",
                    },
                    {
                        "name": "file1",
                        "type": "file"
                    }
                ]
            },
            information_package=ip,
        )
        task.run()

        self.assertTrue(
            os.path.isdir(os.path.join(path, 'dir1'))
        )
        self.assertTrue(
            os.path.isdir(os.path.join(path, 'dir2'))
        )
        self.assertFalse(
            os.path.isfile(os.path.join(path, 'file1'))
        )

        task.undo()

        self.assertFalse(
            os.path.isdir(os.path.join(path, 'dir1'))
        )
        self.assertFalse(
            os.path.isdir(os.path.join(path, 'dir2'))
        )

    def test_submit_sip(self):
        ip = InformationPackage.objects.create(label="ip1")

        srctar = os.path.join(self.preingest_reception, "%s.tar" % ip.pk)
        srcxml = os.path.join(self.preingest_reception, "%s.xml" % ip.pk)
        dsttar = os.path.join(self.ingest_reception, "%s.tar" % ip.pk)
        dstxml = os.path.join(self.ingest_reception, "%s.xml" % ip.pk)
        open(srctar, "a").close()
        open(srcxml, "a").close()

        task = ProcessTask.objects.create(
            name="preingest.tasks.SubmitSIP",
            params={
                "ip": ip.pk
            },
        )
        task.run()

        self.assertTrue(os.path.isfile(dsttar))
        self.assertTrue(os.path.isfile(dstxml))

        task.undo()

        self.assertFalse(os.path.isfile(dsttar))
        self.assertFalse(os.path.isfile(dstxml))
