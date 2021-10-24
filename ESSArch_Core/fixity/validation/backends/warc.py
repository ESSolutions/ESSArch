import logging
import traceback

import click
from django.utils import timezone
from warcio.archiveiterator import ArchiveIterator
from warcio.exceptions import ArchiveLoadFailed

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.warc')


def _read_entire_stream(stream):
    while True:
        piece = stream.read(1024 * 1024)
        if len(piece) == 0:
            break


class WarcValidator(BaseValidator):
    """
    Validates the payload and block digests of WARC records using Warcio
    supports: ``WARC 1.0``, ``WARC 1.1`` or ``ARC``
    """
    def _init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self, filepath):
        """
        Args:
            filepath: Input (w)arc file to validate
        """
        logger.info(f'Validating {filepath} with Warcio')
        passed = True
        message = f'Successfully validated warc {filepath}'
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

        try:
            with open(filepath, 'rb') as stream:
                it = ArchiveIterator(stream, check_digests=True)
                for record in it:
                    digest_present = (record.rec_headers.get_header('WARC-Payload-Digest') or
                                      record.rec_headers.get_header('WARC-Block-Digest'))

                    _read_entire_stream(record.content_stream())

                    d_msg = None
                    output = []

                    rec_id = record.rec_headers.get_header('WARC-Record-ID')
                    rec_type = record.rec_headers.get_header('WARC-Type')
                    rec_offset = it.get_record_offset()

                    if record.digest_checker.passed is False:
                        message = record.digest_checker.problems
                        passed = False
                        raise ValidationError(message)

                    elif record.digest_checker.passed is True:
                        d_msg = 'digest pass'
                    elif record.digest_checker.passed is None:
                        if digest_present and rec_type == 'revisit':
                            d_msg = 'digest present but not checked (revisit)'
                        elif digest_present:  # pragma: no cover
                            # should not happen
                            d_msg = 'digest present but not checked'
                        else:
                            d_msg = 'no digest to check'

                    if d_msg:
                        logger.debug(f'offset {rec_offset} WARC-Record-ID {rec_id} {rec_type} ({d_msg})')
                    if output:
                        logger.debug(f'offset {rec_offset} WARC-Record-ID {rec_id} {rec_type} {output}')

        except ArchiveLoadFailed as e:
            logger.warning(f'Warcio validation of {filepath} failed')
            passed = False
            message = f'<pre>{traceback.format_exc()}</pre>'
            raise ValidationError(f'saw exception ArchiveLoadFailed: {str(e).rstrip()}')

        finally:
            val_obj.message = message
            logger.info(message)
            val_obj.time_done = timezone.now()
            val_obj.passed = passed
            val_obj.save(update_fields=['time_done', 'passed', 'message'])

    @staticmethod
    @click.command()
    @click.argument('path', metavar='INPUT', type=click.Path(exists=True))
    def cli(path):
        validator = WarcValidator()
        try:
            validator.validate(path)
            click.echo('success!')
        except ValidationError as e:
            click.echo(e, err=True)
