import copy
import logging

from django.core.mail import send_mail
from django.template.loader import render_to_string

from ESSArch_Core.WorkflowEngine.models import ProcessTask
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.receipt.backends.base import BaseReceiptBackend

logger = logging.getLogger('essarch.core.fixity.receipt.email')


class EmailReceiptBackend(BaseReceiptBackend):
    def create(self, template, destination, outcome, short_message, message, date, ip=None, task=None):
        logger.debug(u'Sending receipt email to {}'.format(destination))
        subject = short_message

        data = copy.deepcopy(self.data)
        data['outcome'] = outcome
        data['message'] = message
        data['date'] = date
        if task is not None:
            task_obj = ProcessTask.objects.get(pk=task)
            data['task_traceback'] = task_obj.traceback
            data['task_exception'] = task_obj.exception
            data['validations'] = Validation.objects.filter(task=task).order_by('time_started')

        body = render_to_string(template, data)
        send_mail(subject, body, None, [destination], fail_silently=False)
        logger.info(u'Email receipt sent to {}'.format(destination))
