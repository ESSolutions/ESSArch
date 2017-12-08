import logging

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.mediaconch import validate_file as mediaconch_validation
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.mediaconch')


class MediaconchValidator(BaseValidator):
    def validate(self, filepath):
        policy = self.context
        passed, message = mediaconch_validation(filepath, policy)

        if not passed:
            raise ValidationError(message)

        return message
