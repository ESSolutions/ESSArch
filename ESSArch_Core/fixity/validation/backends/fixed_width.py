import logging

from dateutil.parser import parse
from django.utils import timezone

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.fixed_width')


class FixedWidthValidator(BaseValidator):
    invalid_datatype_err = 'Invalid datatype for value {} on row {}, expected {}'
    invalid_datatype_warn = 'Possible invalid datatype for value {} on row {}, expected {}'

    def _create_obj(self, filename, passed, msg):
        return Validation.objects.create(
            filename=filename,
            time_started=timezone.now(),
            time_done=timezone.now(),
            validator=self.__class__.__name__,
            required=self.required,
            task_id=self.task,
            information_package_id=self.ip,
            responsible=self.responsible,
            message=msg,
            passed=passed,
            specification={
                'context': self.context,
                'options': self.options,
            }
        )

    def _validate_str_column(self, field, col, row_number):
        if col.isdigit():
            msg = self.invalid_datatype_warn.format(col, row_number, field['datatype'])
            logger.warning(msg)
            self.warnings += 1
        else:
            float(col)
            msg = self.invalid_datatype_warn.format(col, row_number, field['datatype'])
            logger.warning(msg)
            self.warnings += 1

    def _validate_date_column(self, col):
        try:
            parse(col)
            return True
        except ValueError:
            return False

    def _validate_fields(self, fields, filepath, line, row_number, filler):
        for field in fields:
            if field['end'] - field['start'] != field['length']:
                msg = 'Conflicting field length on row {}: end - start != length'.format(row_number)
                logger.error(msg)
                self.errors += 1
                self._create_obj(filepath, False, msg)

            col = line[field['start']:field['end']]
            cleaned_col = col.rstrip() if filler == ' ' else col.replace(filler, '')

            if field['datatype'] == 'str':
                try:
                    self._validate_str_column(field, cleaned_col, row_number)
                except ValueError:
                    continue

            elif field['datatype'] == 'int':
                try:
                    int(cleaned_col)
                except ValueError:
                    msg = self.invalid_datatype_err.format(col.rstrip(), row_number, field['datatype'])
                    logger.error(msg)
                    self.errors += 1
                    self._create_obj(filepath, False, msg)
                    continue

            elif field['datatype'] == 'float':
                try:
                    float(cleaned_col)
                except ValueError:
                    msg = self.invalid_datatype_err.format(col, row_number, field['datatype'])
                    logger.error(msg)
                    self.errors += 1
                    self._create_obj(filepath, False, msg)
                    continue

            elif field['datatype'] == 'date':
                if not self._validate_date_column(cleaned_col):
                    msg = self.invalid_datatype_err.format(col, row_number, field['datatype'])
                    logger.error(msg)
                    self.errors += 1
                    self._create_obj(filepath, False, msg)

    def _validate_lines(self, filepath, input_file, fields, filler):
        row_number = 0

        for line in input_file:
            row_number += 1
            # Check record length for each line.
            if len(line.replace('\n', '')) != sum([w['length'] for w in fields]):
                msg = 'Invalid record size for post {}'.format(line)
                logger.error(msg)
                self.errors += 1
                self._create_obj(filepath, False, msg)

            self._validate_fields(fields, filepath, line, row_number, filler)

    def _validate(self, filepath, fields, encoding, filler):
        with open(filepath, encoding=encoding) as input_file:
            try:
                self._validate_lines(filepath, input_file, fields, filler)
            except UnicodeDecodeError:
                msg = 'Invalid encoding for filepath {}'.format(filepath)
                logger.exception(msg)
                self.errors += 1
                self._create_obj(filepath, False, msg)

    def validate(self, filepath, expected=None):
        logger.debug('Validating filename of %s' % filepath)

        if expected is None:
            raise ValueError('Expected fields not provided')

        encoding = self.options.get('encoding', 'utf-8')
        filler = self.options.get('filler', ' ')

        self.errors = 0
        self.warnings = 0
        self._validate(filepath, expected, encoding, filler)

        if self.errors > 0:
            msg = 'Fixed-width validation of {} failed with {} error(s)'.format(filepath, self.errors)
            logger.error(msg)
            raise ValidationError(msg)

        logger.info('Successful fixed-width validation of {}'.format(filepath))
