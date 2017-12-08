import logging
import os

import six
from glob2 import glob, iglob
from scandir import walk

from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.structure')


class StructureValidator(BaseValidator):
    """
    Validates that the directory has all the required files and no invalid extensions
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
            if path in glob(valid_path):
                return True

        for valid_path in [p for p in valid_paths if not isinstance(p, six.string_types)]:
            for nested_valid_path in valid_path:
                for found_nested_path, matches in iglob(nested_valid_path, with_matches=True):
                    if found_nested_path == path:
                        # check matches
                        for match in matches:
                            for related_path in valid_path:
                                if related_path != found_nested_path:
                                    related_path = related_path.replace('*', match, 1)

                                    if not os.path.isfile(related_path):
                                        rel_path = os.path.relpath(path, root)
                                        rel_related_path = os.path.relpath(related_path, root)
                                        raise ValidationError('{file} missing related file {related}'.format(file=rel_path, related=rel_related_path))

                        return True

        raise ValidationError('{file} is not allowed'.format(file=path))

    def validate_folder(self, path, node):
        valid_paths = node.get('valid_paths', [])
        required_files = [req.format(**self.data) for req in node.get('required_files', [])]

        for idx, valid in enumerate(valid_paths):
            if isinstance(valid, six.string_types):
                valid_paths[idx] = os.path.join(path, valid).format(**self.data)
            else:
                for nested_idx, nested_valid in enumerate(valid):
                    valid[nested_idx] = os.path.join(path, nested_valid).format(**self.data)

        for root, dirs, files in walk(path):
            for f in files:
                if len(valid_paths):
                    try:
                        self.in_valid_paths(path, os.path.join(root, f), valid_paths)
                    except ValidationError as validation_exc:
                        try:
                            self.update_required_files(os.path.relpath(root, path), f, required_files)
                        except ValueError:
                            raise validation_exc
                        else:
                            pass

                if len(required_files):
                    try:
                        self.update_required_files(os.path.relpath(root, path), f, required_files)
                    except ValueError:
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
