import copy
import json
import logging

from django.template.loader import get_template

from ESSArch_Core.essxml.Generator.xmlGenerator import XMLGenerator
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.receipt.backends.base import BaseReceiptBackend
from ESSArch_Core.fixity.serializers import ValidationSerializer

logger = logging.getLogger('essarch.core.fixity.receipt.xml')


class XMLReceiptBackend(BaseReceiptBackend):
    def create(self, template, destination, outcome, short_message, message, date, ip=None, task=None):
        logger.debug(u'Creating XML receipt: {}'.format(destination))
        spec = json.loads(get_template(template).template.source)
        data = copy.deepcopy(self.data)
        data['outcome'] = outcome
        data['message'] = message
        data['date'] = date
        if task is not None:
            validations = Validation.objects.filter(task=task).order_by('time_started')
            data['validations'] = ValidationSerializer(validations, many=True).data
        files_to_create = {destination: {'spec': spec, 'data': data}}
        XMLGenerator(files_to_create).generate()
        logger.info(u'XML receipt created: {}'.format(destination))
