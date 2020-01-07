import logging

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from ESSArch_Core.exceptions import ESSArchException
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.receipt.backends.base import BaseReceiptBackend
from ESSArch_Core.profiles.utils import fill_specification_data

logger = logging.getLogger('essarch.core.fixity.receipt.email')


class NoEmailRecipientError(ESSArchException):
    pass


class NoEmailSentError(ESSArchException):
    pass


class EmailReceiptBackend(BaseReceiptBackend):
    def create(self, template, destination, outcome, short_message, message, date=None, ip=None, task=None, **kwargs):
        if task is not None and destination is None:
            destination = task.responsible.email

        if not destination:
            msg = 'No recipient set for email'
            logger.error(msg)
            raise NoEmailRecipientError(msg)

        logger.debug('Sending receipt email to {}'.format(destination))
        subject = short_message

        data = {}
        if ip is not None:
            data = fill_specification_data(data=data, ip=ip).to_dict()
        data['outcome'] = outcome
        data['message'] = message
        data['date'] = date or timezone.now()
        if task is not None:
            data['task_traceback'] = task.traceback
            data['task_exception'] = task.exception
            data['validations'] = Validation.objects.filter(task=task).order_by('time_started')

        body = render_to_string(template, data)

        msg = EmailMessage(
            subject,
            body,
            None,
            [destination],
        )

        for attachment in kwargs.get('attachments', []):
            msg.attach_file(attachment)

        msg_count = msg.send(fail_silently=False)

        logger.debug('{} emails sent (including cc and bcc entries)'.format(msg_count))
        if not msg_count:
            raise NoEmailSentError('No emails sent')

        logger.info('Email receipt sent to {}'.format(destination))
