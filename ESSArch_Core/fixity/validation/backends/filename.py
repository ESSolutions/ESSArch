import logging
import re
import traceback

from django.utils import timezone

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.filename')

DEFAULT_EXPECTED = r'^[\da-zA-Z_\-]+\.[\da-zA-Z]+$'


class FilenameValidator(BaseValidator):
    def validate(self, filepath, expected=DEFAULT_EXPECTED):
        logger.debug('Validating filename of %s' % filepath)

        val_obj = Validation(
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

        passed = False
        try:
            if not re.search(expected, filepath):
                message = "Filename validation of {} failed, it does not match {}".format(filepath, expected)
                logger.warning(message)
                raise ValidationError(message)

            passed = True

        except Exception:
            val_obj.message = traceback.format_exc()
            raise
        else:
            val_obj.message = 'Successfully validated filename of {}'.format(filepath)
            logger.info(val_obj.message)
        finally:
            val_obj.time_done = timezone.now()
            val_obj.passed = passed
            val_obj.save()
