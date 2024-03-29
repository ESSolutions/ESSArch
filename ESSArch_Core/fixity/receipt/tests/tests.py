import datetime
import os
import shutil
import tempfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.template.exceptions import TemplateDoesNotExist
from django.test import TestCase
from lxml import etree

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.receipt.backends import email, xml
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.WorkflowEngine.models import ProcessTask

User = get_user_model()


class EmailReceiptBackendTests(TestCase):
    def test_missing_recipient(self):
        self.backend = email.EmailReceiptBackend()

        with self.assertRaises(email.NoEmailRecipientError):
            self.backend.create('receipt/email', None, 'outcome', 'short msg', 'msg')

    def test_empty_recipient(self):
        self.backend = email.EmailReceiptBackend()

        with self.assertRaises(email.NoEmailRecipientError):
            self.backend.create('receipt/email', '', 'outcome', 'short msg', 'msg')

    @mock.patch('ESSArch_Core.fixity.receipt.backends.email.EmailMessage')
    def test_recipient_from_task(self, MockEmailMessage):
        self.backend = email.EmailReceiptBackend()
        user = User.objects.create(email="user@example.com")
        task = ProcessTask.objects.create(responsible=user)

        self.backend.create('receipts/email.txt', None, 'outcome', 'short msg', 'msg', task=task)
        MockEmailMessage.assert_called_once_with(
            "short msg",
            mock.ANY,
            None,
            [user.email],
        )
        MockEmailMessage.return_value.send.assert_called_once_with(fail_silently=False)

    @mock.patch('ESSArch_Core.fixity.receipt.backends.email.EmailMessage')
    def test_recipient_from_arg(self, MockEmailMessage):
        self.backend = email.EmailReceiptBackend()

        self.backend.create('receipts/email.txt', 'custom@example.com', 'outcome', 'short msg', 'msg')
        MockEmailMessage.assert_called_once_with(
            "short msg",
            mock.ANY,
            None,
            ['custom@example.com'],
        )
        MockEmailMessage.return_value.send.assert_called_once_with(fail_silently=False)

    @mock.patch('ESSArch_Core.fixity.receipt.backends.email.EmailMessage')
    def test_recipient_from_arg_and_task(self, MockEmailMessage):
        self.backend = email.EmailReceiptBackend()
        user = User.objects.create(email="user@example.com")
        task = ProcessTask.objects.create(responsible=user)

        self.backend.create('receipts/email.txt', 'custom@example.com', 'outcome', 'short msg', 'msg', task=task)
        MockEmailMessage.assert_called_once_with(
            "short msg",
            mock.ANY,
            None,
            ['custom@example.com'],
        )
        MockEmailMessage.return_value.send.assert_called_once_with(fail_silently=False)

    @mock.patch('ESSArch_Core.fixity.receipt.backends.email.EmailMessage.send', return_value=0)
    def test_invalid_recipient(self, MockEmailMessage):
        self.backend = email.EmailReceiptBackend()
        user = User.objects.create(email="user@example.com")
        task = ProcessTask.objects.create(responsible=user)

        with self.assertRaises(email.NoEmailSentError):
            self.backend.create('receipts/email.txt', 'example', 'outcome', 'short msg', 'msg', task=task)

    @mock.patch('ESSArch_Core.fixity.receipt.backends.email.EmailMessage')
    def test_information_package(self, MockEmailMessage):
        self.backend = email.EmailReceiptBackend()
        ip = InformationPackage.objects.create()
        Path.objects.create(entity='temp')

        self.backend.create(
            'receipts/email.txt',
            'custom@example.com',
            'outcome',
            'short msg',
            'msg',
            ip=ip,
        )
        MockEmailMessage.assert_called_once_with(
            "short msg",
            mock.ANY,
            None,
            ['custom@example.com'],
        )
        MockEmailMessage.return_value.send.assert_called_once_with(fail_silently=False)

    @mock.patch('ESSArch_Core.fixity.receipt.backends.email.EmailMessage')
    def test_attachments(self, MockEmailMessage):
        self.backend = email.EmailReceiptBackend()

        attachments = ['foo/bar.pdf']
        self.backend.create(
            'receipts/email.txt',
            'custom@example.com',
            'outcome',
            'short msg',
            'msg',
            attachments=attachments,
        )
        MockEmailMessage.assert_called_once_with(
            "short msg",
            mock.ANY,
            None,
            ['custom@example.com'],
        )
        MockEmailMessage.return_value.attach_file.assert_called_once_with('foo/bar.pdf')
        MockEmailMessage.return_value.send.assert_called_once_with(fail_silently=False)


class XMLReceiptBackendTests(TestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

    def create_validation(self):
        return Validation.objects.create()

    def create_task(self):
        return ProcessTask.objects.create()

    def test_bad_template(self):
        backend = xml.XMLReceiptBackend()

        with self.assertRaises(TemplateDoesNotExist):
            backend.create(
                template="bad_template",
                destination="some_destination",
                outcome="outcome_data",
                short_message="some_short_message",
                message="some message nothuentohe notehu"
            )

    def test_with_no_ip_should_create_xml(self):
        backend = xml.XMLReceiptBackend()
        dest_file_path = os.path.join(self.datadir, "dest_file.xml")

        backend.create(
            template="receipts/xml.json",
            destination=dest_file_path,
            outcome="outcome data",
            short_message="some short message",
            message="some longer message",
        )

        expected_attributes = {
            'outcome': 'outcome data',
            'message': 'some longer message'
        }

        root_xml = etree.parse(dest_file_path)
        status_el = root_xml.xpath("/receipt/status")[0]
        datetime_el = root_xml.xpath("/receipt/datetime")[0]

        self.assertEqual(status_el.attrib, expected_attributes)
        self.assertIsNotNone(datetime_el.text)

    def test_with_no_ip_and_date_passed_should_create_xml(self):
        backend = xml.XMLReceiptBackend()
        dest_file_path = os.path.join(self.datadir, "dest_file.xml")

        datetime_now = datetime.datetime.now()

        backend.create(
            template="receipts/xml.json",
            destination=dest_file_path,
            outcome="outcome data",
            short_message="some short message",
            message="some longer message",
            date=datetime_now,
        )

        expected_attributes = {
            'outcome': 'outcome data',
            'message': 'some longer message'
        }

        root_xml = etree.parse(dest_file_path)
        status_el = root_xml.xpath("/receipt/status")[0]
        datetime_el = root_xml.xpath("/receipt/datetime")[0]

        self.assertEqual(status_el.attrib, expected_attributes)
        self.assertEqual(datetime_el.text, datetime_now.isoformat())

    def test_with_tasks_passed_should_be_added_to_xml(self):
        backend = xml.XMLReceiptBackend()
        task = self.create_task()
        validation = self.create_validation()
        validation.task = task
        validation.passed = True
        validation.save()

        dest_file_path = os.path.join(self.datadir, "dest_file.xml")

        backend.create(
            template="receipts/xml.json",
            destination=dest_file_path,
            outcome="outcome data",
            short_message="some short message",
            message="some longer message",
            task=task,
        )

        expected_status_attributes = {
            'outcome': 'outcome data',
            'message': 'some longer message'
        }

        expected_validation_attributes = {
            'passed': 'true'
        }

        root_xml = etree.parse(dest_file_path)
        status_el = root_xml.xpath("/receipt/status")[0]
        datetime_el = root_xml.xpath("/receipt/datetime")[0]
        validations_el = root_xml.xpath("/receipt/validations/validation")

        self.assertEqual(status_el.attrib, expected_status_attributes)
        self.assertIsNotNone(datetime_el.text)
        self.assertEqual(len(validations_el), 1)
        self.assertEqual(validations_el[0].attrib, expected_validation_attributes)
