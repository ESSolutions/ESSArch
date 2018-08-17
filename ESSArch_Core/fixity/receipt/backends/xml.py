# -*- coding: utf-8 -*-

import copy
import json
import logging

from django.template.loader import get_template
from elasticsearch_dsl import Q, Search
from lxml import etree

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

        data[u'ärenden'] = []
        if ip is not None:
            cts = ip.get_content_type_file()
            if cts is not None:
                tree = etree.parse(cts)
                for arende in tree.xpath("//*[local-name()='ArkivobjektArende']"):
                    arende_id = arende.xpath("*[local-name()='ArkivobjektID']")[0].text
                    a_data = {'ArkivobjektID': arende_id}

                    try:
                        a_data['id'] = Search(index=['component']).filter('bool', must=[Q('term', type="Ärende"), Q('term', **{'reference_code.keyword': arende_id}), Q('term', ip=str(ip.pk))]).execute().hits[0].meta.id
                    except KeyError:
                        pass
                    data[u'ärenden'].append(a_data)

        files_to_create = {destination: {'spec': spec, 'data': data}}
        XMLGenerator().generate(files_to_create)
        logger.info(u'XML receipt created: {}'.format(destination))
