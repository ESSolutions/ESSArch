import logging
import traceback
import zipfile

import click
import msoffcrypto
import olefile
from django.utils import timezone

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.encryption')


class FileEncryptionValidator(BaseValidator):
    """
    Validates if a file is encrypted or not.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def _validate_ole_file(filepath):
        with open(filepath, "rb") as f:
            officefile = msoffcrypto.OfficeFile(f)
            return officefile.is_encrypted()

    @staticmethod
    def _validate_zip_file(filepath):
        zf = zipfile.ZipFile(filepath)
        for zinfo in zf.infolist():
            is_encrypted = zinfo.flag_bits & 0x1
            if is_encrypted:
                return True

        return False

    @staticmethod
    def is_file_encrypted(filepath):
        if olefile.isOleFile(filepath):
            return FileEncryptionValidator._validate_ole_file(filepath)
        elif zipfile.is_zipfile(filepath):
            return FileEncryptionValidator._validate_zip_file(filepath)

        return None

    def validate(self, filepath, expected=None):
        logger.debug('Validating encryption of %s' % filepath)
        result = self.is_file_encrypted(filepath)

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
            if result is not None and result != expected:
                if expected is True:
                    expected_msg = "{} is expected to be encrypted"
                else:
                    expected_msg = "{} is not expected to be encrypted"

                raise ValidationError(expected_msg.format(filepath))

            passed = True

        except ValidationError:
            val_obj.message = traceback.format_exc()
            raise
        else:
            message = 'Successfully validated encryption of %s' % filepath
            val_obj.message = message
            logger.info(message)
        finally:
            val_obj.time_done = timezone.now()
            val_obj.passed = passed
            val_obj.save(update_fields=['time_done', 'passed', 'message'])

    @staticmethod
    @click.command()
    @click.argument('path', metavar='INPUT', type=click.Path(exists=True))
    @click.argument('expected', type=bool)
    def cli(path, expected):
        validator = FileEncryptionValidator()
        validator.validate(path, expected=expected)
