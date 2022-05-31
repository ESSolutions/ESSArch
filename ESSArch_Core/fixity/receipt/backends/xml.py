# -*- coding: utf-8 -*-

import json
import logging
import os

from django.template.loader import get_template
from django.utils import timezone
from lxml import etree

from ESSArch_Core.essxml.Generator.xmlGenerator import XMLGenerator
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.receipt.backends.base import BaseReceiptBackend
from ESSArch_Core.fixity.serializers import ValidationSerializer
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.tags.models import TagVersion

logger = logging.getLogger('essarch.core.fixity.receipt.xml')


class XMLReceiptBackend(BaseReceiptBackend):
    def create(self, template, destination, outcome, short_message, message, date=None, ip=None, task=None, **kwargs):
        logger.debug('Creating XML receipt: {}'.format(destination))
        spec = json.loads(get_template(template).template.source)

        data = {}
        if ip is not None:
            data = fill_specification_data(data=data, ip=ip)
        data['outcome'] = outcome
        data['message'] = message
        data['date'] = date or timezone.now()
        if task is not None:
            validations = Validation.objects.filter(task=task).order_by('time_started')
            data['validations'] = ValidationSerializer(validations, many=True).data

        files_to_create = {destination: {'spec': spec, 'data': data}}
        XMLGenerator().generate(files_to_create)
        logger.info('XML receipt created: {}'.format(destination))

        return destination
