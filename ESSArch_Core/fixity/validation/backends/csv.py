import csv
import logging

import click

from django.utils import timezone

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.csv')


class CSVValidator(BaseValidator):
    def _create_obj(self, filename, passed, msg):
        return Validation(
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

    def _validate(self, path, column_number, delimiter=',', encoding=None):
        validation_objs = []

        with open(path, 'r', encoding=encoding) as csvfile:
            for row in csvfile:
                # Check that row ends with line break
                if not row.endswith('\n'):
                    msg = 'Missing line break for post {}'.format(row)
                    logging.error(msg)
                    validation_objs.append(self._create_obj(path, False, msg))

            csvfile.seek(0)
            reader = csv.reader(csvfile, delimiter=delimiter, quotechar='"')

            for row in reader:
                if len(row) != column_number:
                    msg = 'Wrong delimiter for post {}'.format(row)
                    logging.error(msg)
                    validation_objs.append(self._create_obj(path, False, msg))

        Validation.objects.bulk_create(validation_objs, batch_size=100)
        return [o.message for o in validation_objs]

    def validate(self, filepath, expected=None, encoding=None):
        logger.debug('Validating csv: %s' % filepath)
        time_started = timezone.now()

        column_number = self.options['column_number']
        delimiter = self.options.get('delimiter', ',')

        try:
            errors = self._validate(filepath, column_number, delimiter, encoding)

        except Exception:
            logger.exception('Unknown error occurred when validating {}'.format(filepath))
            raise
        else:
            if len(errors) > 0:
                msg = 'CSV validation of {} failed with {} error(s)'.format(filepath, len(errors))
                logger.error(msg)
                raise ValidationError(msg, errors=errors)

            message = 'Successfully validated csv: {}'.format(filepath)
            time_done = timezone.now()
            Validation.objects.create(
                filename=filepath,
                validator=self.__class__.__name__,
                required=self.required,
                task=self.task,
                information_package=self.ip,
                responsible=self.responsible,
                passed=True,
                message=message,
                time_started=time_started,
                time_done=time_done,
                specification={
                    'context': self.context,
                    'options': self.options,
                }
            )
            logger.info(message)

    @staticmethod
    @click.command()
    @click.argument('path', metavar='INPUT', type=click.Path(exists=True))
    @click.argument('cols', type=int, metavar='COLUMN_NUMBER')
    @click.option('--delimiter', type=str, default=',', show_default=True)
    @click.option('--encoding', type=str)
    def cli(path, cols, delimiter, encoding):
        options = {'column_number': cols, 'delimiter': delimiter}
        validator = CSVValidator(options=options)

        try:
            validator.validate(path, encoding=encoding)
        except ValidationError as e:
            click.echo(e, err=True)
            for error in e.errors:
                click.echo(error, err=True)
