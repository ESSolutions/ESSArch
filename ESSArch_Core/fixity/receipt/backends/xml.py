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

        data['ärenden'] = []
        data['makulerat'] = "false"
        if ip is not None:
            cts = ip.get_content_type_file()
            if cts is not None and os.path.isfile(cts):
                tree = etree.parse(ip.open_file(cts, 'rb'))
                for arende in tree.xpath("//*[local-name()='ArkivobjektArende']"):
                    arende_mening = arende.xpath("*[local-name()='Arendemening']")[0].text
                    if arende_mening == 'Makulerat':
                        data['makulerat'] = "true"

                    arende_id = arende.xpath("*[local-name()='ArkivobjektID']")[0].text
                    tv = TagVersion.objects.get(
                        reference_code=arende_id,
                        tag__information_package=ip,
                    )
                    a_data = {'id': str(tv.pk), 'ArkivobjektID': arende_id}

                    try:
                        recno = arende.xpath(
                            ".//*[local-name()='EgetElement' and @Namn='Recno']/*[local-name()='Varde']"
                        )[0].text
                        a_data['Recno'] = recno
                    except IndexError:
                        logger.error('No Recno found for {}'.format(arende_id))

                    data['ärenden'].append(a_data)
            else:
                logger.debug('No file found at {}'.format(cts))

        files_to_create = {destination: {'spec': spec, 'data': data}}
        XMLGenerator().generate(files_to_create)
        logger.info('XML receipt created: {}'.format(destination))

        return destination
