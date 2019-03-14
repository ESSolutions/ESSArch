import logging
import re
import traceback

from django.utils import timezone

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.repeated_extension')

REPEATED_PATTERN = r'\.(\w+).\1'


class RepeatedExtensionValidator(BaseValidator):
    def validate(self, filepath):
        logger.debug('Validating extension of %s' % filepath)

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
            if re.search(REPEATED_PATTERN, filepath):
                message = "Extension validation of {} failed, repeated extensions found".format(filepath)
                logger.warning(message)
                raise ValidationError(message)

            passed = True

        except Exception:
            val_obj.message = traceback.format_exc()
            raise
        else:
            val_obj.message = 'Successfully validated extension of {}'.format(filepath)
            logger.info(val_obj.message)
        finally:
            val_obj.time_done = timezone.now()
            val_obj.passed = passed
            val_obj.save()
