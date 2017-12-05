import logging
import os

from glob2 import glob, iglob

from scandir import scandir

import six

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.structure')


class StructureValidator(BaseValidator):
    """
    Validates that the directory has all the required files and no invalid extensions
    """

    file_validator = False

    def validate_folder(self, path, node):
        valid_extensions = [ext.format(**self.data) for ext in node.get('valid_extensions', [])]
        valid_paths = node.get('valid_paths', [])
        required_files = [req.format(**self.data) for req in node.get('required_files', [])]

        for idx, valid in enumerate(valid_paths):
            if isinstance(valid, six.string_types):
                valid_paths[idx] = os.path.join(path, valid).format(**self.data)
            else:
                for nested_idx, nested_valid in enumerate(valid):
                    valid[nested_idx] = os.path.join(path, nested_valid).format(**self.data)

        for entry in scandir(path):
            if entry.is_dir():
                continue

            try:
                required_files.remove(entry.name)
            except ValueError:
                pass
            else:
                continue

            if len(valid_paths):
                valid = False
                for valid_path in valid_paths:
                    if isinstance(valid_path, six.string_types):
                        if entry.path in glob(valid_path):
                            valid = True
                            break
                    else:
                        # valid is a list of strings. The entry must match one
                        # of them and the remaining strings (wildcards replaced)
                        # must match a file too

                        found = False
                        for nested_valid in valid_path:
                            for nested_valid_path, matches in iglob(nested_valid, with_matches=True):
                                if nested_valid_path == entry.path:
                                    found = True
                                    break

                            if found:
                                break

                        if not found:
                            break

                        for nested_valid in valid_path:
                            for match in matches:
                                nested_valid = nested_valid.replace('*', match, 1)

                            if not os.path.isfile(nested_valid):
                                raise ValidationError('{file} missing related file {related}'.format(file=entry.path, related=nested_valid))

                        valid = True

                if not valid:
                    raise ValidationError('{file} is not allowed'.format(file=entry.path))

            filepath, ext = os.path.splitext(entry.path)
            if len(valid_extensions) and not ext[1:] in valid_extensions:
                raise ValidationError('{file} does not have a valid extension'.format(file=entry.path))

            try:
                # delete entry from required list
                required_files.remove(entry.path)
            except ValueError:
                # the entry is not in the required list
                pass

        if len(required_files):
            raise ValidationError('Missing {files} in {path}'.format(files=','.join(required_files), path=path))

    def validate(self, filepath, expected=None):
        root = self.options.get('tree', [])

        for node in root:
            if node['type'] == 'root':
                self.validate_folder(filepath, node)
            elif node['type'] == 'folder':
                self.validate_folder(os.path.join(filepath, node['name']), node)
