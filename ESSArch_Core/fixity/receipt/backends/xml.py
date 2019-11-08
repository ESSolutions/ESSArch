# -*- coding: utf-8 -*-

import json
import logging
import os

from django.template.loader import get_template
from django.utils import timezone
from elasticsearch_dsl import Q, Search
from lxml import etree

from ESSArch_Core.essxml.Generator.xmlGenerator import XMLGenerator
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.receipt.backends.base import BaseReceiptBackend
from ESSArch_Core.fixity.serializers import ValidationSerializer
from ESSArch_Core.profiles.utils import fill_specification_data

logger = logging.getLogger('essarch.core.fixity.receipt.xml')


class XMLReceiptBackend(BaseReceiptBackend):
    def create(self, template, destination, outcome, short_message, message, date=None, ip=None, task=None):
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

        data['ärenden'] = []
        if ip is not None:
            cts = ip.get_content_type_file()
            if cts is not None and os.path.isfile(cts):
                tree = etree.parse(ip.open_file(cts))
                for arende in tree.xpath("//*[local-name()='ArkivobjektArende']"):
                    arende_id = arende.xpath("*[local-name()='ArkivobjektID']")[0].text
                    a_data = {'ArkivobjektID': arende_id}

                    try:
                        a_data['id'] = Search(index=['component']).filter(
                            'bool', must=[
                                Q('term', type="Ärende"),
                                Q('term', **{'reference_code.keyword': arende_id}),
                                Q('term', ip=str(ip.pk))
                            ]
                        ).execute().hits[0].meta.id
                    except IndexError:
                        pass
                    data['ärenden'].append(a_data)
            else:
                logger.debug('No file found at {}'.format(cts))

        files_to_create = {destination: {'spec': spec, 'data': data}}
        XMLGenerator().generate(files_to_create)
        logger.info('XML receipt created: {}'.format(destination))
