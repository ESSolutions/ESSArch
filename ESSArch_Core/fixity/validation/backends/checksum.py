import logging
import os

from django.utils import timezone
from rest_framework import serializers

from ESSArch_Core.essxml.util import find_file
from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.checksum import calculate_checksum
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.checksum')


class ChecksumValidator(BaseValidator):
    """
    Validates the checksum of a file against the given ``context``.

    * ``context`` specifies how the input is given and must be one of
      ``checksum_file``, ``checksum_str`` and ``xml_file``
    * ``options``

       * ``algorithm`` must be one of ``md5``, ``sha-1``, ``sha-224``,
         ``sha-256``, ``sha-384`` and ``sha-512``. Defaults to ``md5``
       * ``block_size``: Defaults to 65536
    """

    label = 'Checksum Validator'

    @classmethod
    def get_form(cls):
        return [
            {
                'key': 'path',
                'type': 'input',
                'templateOptions': {
                    'label': 'Path to validate',
                    'required': True,
                }
            },
            {
                'key': 'options.algorithm',
                'type': 'select',
                'defaultValue': 'SHA-256',
                'templateOptions': {
                    'label': 'Checksum algorithm',
                    'required': True,
                    'labelProp': 'name',
                    'valueProp': 'value',
                    'options': [
                        {'name': 'MD5', 'value': 'MD5'},
                        {'name': 'SHA-1', 'value': 'SHA-1'},
                        {'name': 'SHA-224', 'value': 'SHA-224'},
                        {'name': 'SHA-256', 'value': 'SHA-256'},
                        {'name': 'SHA-384', 'value': 'SHA-384'},
                        {'name': 'SHA-512', 'value': 'SHA-512'},
                    ]
                }
            },
            {
                'key': 'options.expected',
                'type': 'input',
                'templateOptions': {
                    'label': 'Checksum',
                    'required': True,
                }
            },
        ]

    class Serializer(BaseValidator.Serializer):
        context = serializers.CharField(default='checksum_str')
        block_size = serializers.IntegerField(default=65536)

    class OptionsSerializer(BaseValidator.OptionsSerializer):
        expected = serializers.CharField()
        algorithm = serializers.ChoiceField(
            choices=['MD5', 'SHA-1', 'SHA-224', 'SHA-256', 'SHA-384', 'SHA-512'],
            default='SHA-256',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.context:
            raise ValueError('Need something to compare to')

        self.algorithm = self.options.get('algorithm', 'md5')
        self.block_size = self.options.get('block_size', 65536)

    def validate(self, filepath, expected=None):
        logger.debug('Validating checksum of %s' % filepath)

        if self.ip is not None:
            relpath = os.path.relpath(filepath, self.ip.object_path)
        else:
            relpath = filepath

        val_obj = Validation.objects.create(
            filename=relpath,
            time_started=timezone.now(),
            validator=self.__class__.__name__,
            required=self.required,
            task=self.task,
            information_package=self.ip,
            responsible=self.responsible,
            specification={
                'context': self.context,
                'options': self.options,
            }
        )

        expected = self.options['expected'].format(**self.data)

        if self.context == 'checksum_str':
            checksum = expected.lower()
        elif self.context == 'checksum_file':
            with open(expected, 'r') as checksum_file:
                checksum = checksum_file.read().strip()
        elif self.context == 'xml_file':
            xml_el, _ = find_file(filepath, xmlfile=expected)
            checksum = xml_el.checksum

        passed = False
        try:
            actual_checksum = calculate_checksum(filepath, algorithm=self.algorithm, block_size=self.block_size)
            if actual_checksum != checksum:
                raise ValidationError("checksum for %s is not valid (%s != %s)" % (
                    relpath, checksum, actual_checksum
                ))
            passed = True
        except Exception as e:
            val_obj.message = str(e)
            raise
        else:
            message = 'Successfully validated checksum of %s' % relpath
            val_obj.message = message
            logger.info(message)
        finally:
            val_obj.time_done = timezone.now()
            val_obj.passed = passed
            val_obj.save(update_fields=['time_done', 'passed', 'message'])
