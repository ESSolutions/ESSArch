import unittest.mock
from django.contrib.auth import get_user_model
from django.test import TestCase

from ESSArch_Core.fixity.receipt.backends import email
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

    @mock.patch('ESSArch_Core.fixity.receipt.backends.email.send_mail')
    def test_recipient_from_task(self, mock_send_mail):
        self.backend = email.EmailReceiptBackend()
        user = User.objects.create(email="user@example.com")
        task = ProcessTask.objects.create(responsible=user)

        self.backend.create('receipts/email.txt', None, 'outcome', 'short msg', 'msg', task=task.pk)
        mock_send_mail.assert_called_once_with('short msg', mock.ANY, None, [user.email], fail_silently=False)

    @mock.patch('ESSArch_Core.fixity.receipt.backends.email.send_mail')
    def test_recipient_from_arg(self, mock_mail):
        self.backend = email.EmailReceiptBackend()

        self.backend.create('receipts/email.txt', 'custom@example.com', 'outcome', 'short msg', 'msg')
        mock_mail.assert_called_once_with('short msg', mock.ANY, None, ['custom@example.com'], fail_silently=False)

    @mock.patch('ESSArch_Core.fixity.receipt.backends.email.send_mail')
    def test_recipient_from_arg_and_task(self, mock_mail):
        self.backend = email.EmailReceiptBackend()
        user = User.objects.create(email="user@example.com")
        task = ProcessTask.objects.create(responsible=user)

        self.backend.create('receipts/email.txt', 'custom@example.com', 'outcome', 'short msg', 'msg', task=task.pk)
        mock_mail.assert_called_once_with('short msg', mock.ANY, None, ['custom@example.com'], fail_silently=False)

    @mock.patch('ESSArch_Core.fixity.receipt.backends.email.send_mail', return_value=0)
    def test_invalid_recipient(self, mock_mail):
        self.backend = email.EmailReceiptBackend()
        user = User.objects.create(email="user@example.com")
        task = ProcessTask.objects.create(responsible=user)

        with self.assertRaises(email.NoEmailSentError):
            self.backend.create('receipts/email.txt', 'example', 'outcome', 'short msg', 'msg', task=task.pk)
