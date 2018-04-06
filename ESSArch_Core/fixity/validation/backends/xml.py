import logging
import os

from django.utils import timezone

from ESSArch_Core.essxml.util import find_files
from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.checksum import calculate_checksum
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.xml')


class DiffCheckValidator(BaseValidator):
    """
    Validates the file against a given XML to see if is an entirely new file or
    if it has been changed or renamed/moved.

    The post validation checks if there are files that has been deleted after
    the XML was generated.
    """

    def __init__(self, *args, **kwargs):
        super(DiffCheckValidator, self).__init__(*args, **kwargs)

        if not self.context:
            raise ValueError('A context (xml) is required')

        rootdir = self.options.get('rootdir')
        self.default_algorithm = self.options.get('default_algorithm', 'SHA-256')

        self.present             = {}  # Map checksum -> fname
        self.deleted             = {}  # Map checksum -> fname
        self.checksums           = {}  # Map fname -> checksum
        self.checksum_algorithms = {}  # Map fname -> checksum algorithm

        self.logical_files = find_files(self.context)
        for logical in self.logical_files:
            if rootdir is not None:
                logical_path = os.path.join(rootdir, logical.path)
            else:
                logical_path = logical.path

            self.deleted[logical.checksum] = logical_path
            self.present[logical.checksum] = logical_path
            self.checksums[logical_path] = logical.checksum
            self.checksum_algorithms[logical_path] = logical.checksum_type

    def _validate(self, filepath):
        algorithm = self.checksum_algorithms.get(filepath, self.default_algorithm)
        newhash = calculate_checksum(filepath, algorithm=algorithm)

        self.deleted.pop(newhash, None)

        if newhash in self.present:
            oldname = self.present[newhash]
            if filepath not in self.checksums:
                if oldname.lower() != filepath.lower():
                    raise ValidationError('{old} has been renamed to {new}'.format(old=self.present[newhash], new=filepath))
        elif filepath in self.checksums:
            oldhash = self.checksums[filepath]
            if oldhash != newhash:
                self.deleted.pop(oldhash, None)
                raise ValidationError('{file} has been changed'.format(file=filepath))
        elif filepath not in self.checksums:
            raise ValidationError('{file} has been added'.format(file=filepath))

    def validate(self, filepath):
        xmlfile = self.context
        logger.debug('Validating {file} against {xml}'.format(file=filepath, xml=xmlfile))

        try:
            self._validate(filepath)
        except Exception as e:
            logger.warn('Validation of {file} against {xml} failed, {msg}'.format(file=filepath, xml=xmlfile, msg=e.message))
            raise

        logger.info("Successful validation of {file} against {xml}".format(file=filepath, xml=xmlfile))

    def post_validation(self):
        for deleted in self.deleted:
            msg = '{file} has been deleted'.format(file=deleted)
            logger.warn('Validation of {file} against {xml} failed, {msg}'.format(file=deleted, xml=self.context, msg=msg))
            Validation.objects.create(
                filename=deleted,
                time_started=timezone.now(),
                time_done=timezone.now(),
                validator=self.__class__.__name__,
                required=self.required,
                information_package=self.ip,
                responsible=self.responsible,
                message=msg,
                passed=False,
                specification={
                    'context': self.context,
                    'options': self.options,
                }
            )

        if len(self.deleted):
            raise ValidationError('{len} file(s) has been deleted'.format(len=len(self.deleted)))
