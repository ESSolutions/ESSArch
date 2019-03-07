import csv
import logging

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

    def _validate(self, path, column_number, delimiter=','):
        validation_objs = []

        with open(path, 'r') as csvfile:
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
        return len(validation_objs)

    def validate(self, filepath, expected=None):
        logger.debug('Validating csv: %s' % filepath)
        time_started = timezone.now()

        column_number = self.options['column_number']
        delimiter = self.options.get('delimiter', ',')

        try:
            error_num = self._validate(filepath, column_number, delimiter)
        except Exception:
            logger.exception('Unknown error occurred when validating {}'.format(filepath))
            raise
        else:
            if error_num > 0:
                msg = 'CSV validation of {} failed with {} errors'.format(filepath, error_num)
                logger.error(msg)
                raise ValidationError(msg)

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
