import logging
import traceback

from django.utils import timezone

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

    def __init__(self, *args, **kwargs):
        super(ChecksumValidator, self).__init__(*args, **kwargs)

        if not self.context:
            raise ValueError('Need something to compare to')

        self.algorithm = self.options.get('algorithm', 'md5')
        self.block_size = self.options.get('block_size', 65536)

    def validate(self, filepath, expected=None):
        logger.debug('Validating checksum of %s' % filepath)
        val_obj = Validation.objects.create(
            filename=filepath,
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
                raise ValidationError("checksum for %s is not valid (%s != %s)" % (filepath, checksum, actual_checksum))
            passed = True
        except Exception:
            val_obj.message = traceback.format_exc()
            raise
        else:
            message = u'Successfully validated checksum of %s' % filepath
            val_obj.message = message
            logger.info(message)
        finally:
            val_obj.time_done = timezone.now()
            val_obj.passed = passed
            val_obj.save(update_fields=['time_done', 'passed', 'message'])
