import logging
import traceback

from django.utils import timezone

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.format import FormatIdentifier
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.format')


class FormatValidator(BaseValidator):
    """
    Validates the format of a file against the given ``context``.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        allow_unknown = self.options.get('allow_unknown_file_types', False)
        self.fid = FormatIdentifier(allow_unknown_file_types=allow_unknown)

    def validate(self, filepath, expected=None):
        logger.debug('Validating format of %s' % filepath)

        name, version, reg_key = expected
        if not any(f is not None for f in (name, version, reg_key)):
            raise ValueError('At least one of name, version and registry key is required')

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

        passed = False
        try:
            actual_name, actual_version, actual_reg_key = self.fid.identify_file_format(filepath)
            if name and name != actual_name:
                raise ValidationError("format name for {} is not valid, ({} !={})"
                                      .format(filepath, name, actual_name))
            if version and version != actual_version:
                raise ValidationError("format version for {} is not valid, ({} != {})"
                                      .format(filepath, version, actual_version))
            if reg_key and reg_key != actual_reg_key:
                raise ValidationError("format registry key for {} is not valid, ({} != {})"
                                      .format(filepath, reg_key, actual_reg_key))

            passed = True
        except ValidationError:
            val_obj.message = traceback.format_exc()
            raise
        else:
            message = 'Successfully validated checksum of %s' % filepath
            val_obj.message = message
            logger.info(message)
        finally:
            val_obj.time_done = timezone.now()
            val_obj.passed = passed
            val_obj.save(update_fields=['time_done', 'passed', 'message'])
