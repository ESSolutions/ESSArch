from __future__ import unicode_literals

import logging
import os
import traceback

import six
from django.utils import timezone
from glob2 import glob, iglob
from scandir import walk

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.base import BaseValidator
from ESSArch_Core.util import normalize_path

logger = logging.getLogger('essarch.fixity.validation.structure')


class StructureValidator(BaseValidator):
    """
    Validates that the directory has all the required files and no invalid
    extensions.

    The ``tree`` option specifies a set of rules for directories:

    * ``type`` must be either ``root`` or ``folder`` and is only used to
      specify if we are at the root or not. If ``folder`` is specified then we
      also require the ``name`` option to be specified.
    * ``name`` tells us which folder is being described
    * ``required_files`` is a list with files that must be in the directory
    * ``valid_paths`` is a list of strings and/or lists that are allowed in the
      directory. Wildcards can be specified using ``*``.

      Inner lists are used to specify valid file groups. E.g.
      ``[['*.doc', '*.pdf']]`` says that for each .doc file there must be a
      .pdf file with the same name.

    """

    file_validator = False

    def update_required_files(self, rel_dir, filename, required_files):
        if rel_dir == '.':
            rel_file = filename
        else:
            rel_file = os.path.join(rel_dir, filename)

        required_files.remove(rel_file)

    def in_valid_paths(self, root, path, valid_paths):
        for valid_path in [p for p in valid_paths if isinstance(p, six.string_types)]:
            if path in list(six.moves.map(normalize_path, glob(valid_path))):
                return True

        for valid_path in [p for p in valid_paths if not isinstance(p, six.string_types)]:
            for nested_valid_path in valid_path:
                for found_nested_path, matches in iglob(nested_valid_path, with_matches=True):
                    found_nested_path = normalize_path(found_nested_path)
                    if found_nested_path == path:
                        # check matches
                        matches = six.moves.map(normalize_path, matches)
                        for match in matches:
                            for related_path in valid_path:
                                if related_path != found_nested_path:
                                    related_path = related_path.replace('*', match, 1)

                                    if not os.path.isfile(related_path):
                                        rel_path = normalize_path(os.path.relpath(path, root))
                                        rel_related_path = normalize_path(os.path.relpath(related_path, root))
                                        raise ValidationError('{file} missing related file {related}'.format(file=rel_path, related=rel_related_path))

                        return True

        raise ValidationError('{file} is not allowed'.format(file=path))

    def validate_folder(self, path, node):
        valid_paths = node.get('valid_paths', [])
        allow_empty = node.get('allow_empty', True)
        required_files = list(six.moves.map(normalize_path, [req.format(**self.data) for req in node.get('required_files', [])]))
        file_count = 0

        for idx, valid in enumerate(valid_paths):
            if isinstance(valid, six.string_types):
                valid_paths[idx] = normalize_path(os.path.join(path, valid).format(**self.data))
            else:
                for nested_idx, nested_valid in enumerate(valid):
                    valid[nested_idx] = normalize_path(os.path.join(path, nested_valid).format(**self.data))

        for root, dirs, files in walk(path):
            for f in files:
                file_count += 1
                if len(valid_paths):
                    try:
                        self.in_valid_paths(path, normalize_path(os.path.join(root, f)), valid_paths)
                    except ValidationError as validation_exc:
                        try:
                            self.update_required_files(os.path.relpath(root, path), f, required_files)
                        except ValueError:
                            raise validation_exc

                if len(required_files):
                    try:
                        self.update_required_files(os.path.relpath(root, path), f, required_files)
                    except ValueError:
                        pass

        if not allow_empty and file_count == 0:
            raise ValidationError('{path} is not allowed to be empty'.format(path=path))

        if len(required_files):
            raise ValidationError('Missing {files} in {path}'.format(files=','.join(required_files), path=path))

    def validate(self, filepath, expected=None):
        root = self.options.get('tree', [])
        filepath = normalize_path(filepath)
        logger.debug("Validating structure of %s" % filepath)

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
            for node in root:
                if node['type'] == 'root':
                    self.validate_folder(filepath, node)
                elif node['type'] == 'folder':
                    self.validate_folder(os.path.join(filepath, node['name']), node)

            passed = True
        except Exception:
            logger.exception("Structure validation of {} failed".format(filepath))
            val_obj.message = traceback.format_exc()
            raise
        else:
            message = "Successful Mediaconch validation of %s" % filepath
            val_obj.message = message
            logger.info(message)
        finally:
            val_obj.time_done = timezone.now()
            val_obj.passed = passed
            val_obj.save(update_fields=['time_done', 'passed', 'message'])

        return message
