import copy
import logging

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from ESSArch_Core.WorkflowEngine.models import ProcessTask
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.receipt.backends.base import BaseReceiptBackend
from ESSArch_Core.profiles.utils import fill_specification_data

logger = logging.getLogger('essarch.core.fixity.receipt.email')


class NoEmailRecipientError(Exception):
    pass


class NoEmailSentError(Exception):
    pass


class EmailReceiptBackend(BaseReceiptBackend):
    def create(self, template, destination, outcome, short_message, message, date=None, ip=None, task=None):
        try:
            task_obj = ProcessTask.objects.get(pk=task)
        except ProcessTask.DoesNotExist:
            task_obj = None
        else:
            if destination is None:
                destination = task_obj.responsible.email

        if not destination:
            msg = 'No recipient set for email'
            logger.error(msg)
            raise NoEmailRecipientError(msg)

        logger.debug(u'Sending receipt email to {}'.format(destination))
        subject = short_message

        data = {}
        if ip is not None:
            data = fill_specification_data(data=data, ip=ip)
        data['outcome'] = outcome
        data['message'] = message
        data['date'] = date or timezone.now()
        if task_obj is not None:
            data['task_traceback'] = task_obj.traceback
            data['task_exception'] = task_obj.exception
            data['validations'] = Validation.objects.filter(task=task).order_by('time_started')

        body = render_to_string(template, data)
        msg_count = send_mail(subject, body, None, [destination], fail_silently=False)

        logger.debug(u'{} emails sent (including cc and bcc entries)'.format(msg_count))
        if not msg_count:
            raise NoEmailSentError('No emails sent')

        logger.info(u'Email receipt sent to {}'.format(destination))
