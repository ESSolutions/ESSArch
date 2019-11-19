import errno
import importlib
import logging
import os
from os import walk

from django.conf import settings
from glob2 import glob

logger = logging.getLogger('essarch.fixity.validation')

AVAILABLE_VALIDATORS = {
    'checksum': 'ESSArch_Core.fixity.validation.backends.checksum.ChecksumValidator',
    'csv': 'ESSArch_Core.fixity.validation.backends.csv.CSVValidator',
    'diff_check': 'ESSArch_Core.fixity.validation.backends.xml.DiffCheckValidator',
    'encryption': 'ESSArch_Core.fixity.validation.backends.encryption.FileEncryptionValidator',
    'filename': 'ESSArch_Core.fixity.validation.backends.filename.FilenameValidator',
    'fixed_width': 'ESSArch_Core.fixity.validation.backends.fixed_width.FixedWidthValidator',
    'format': 'ESSArch_Core.fixity.validation.backends.format.FormatValidator',
    'mediaconch': 'ESSArch_Core.fixity.validation.backends.mediaconch.MediaconchValidator',
    'repeated_extension': 'ESSArch_Core.fixity.validation.backends.repeated_extension.RepeatedExtensionValidator',
    'structure': 'ESSArch_Core.fixity.validation.backends.structure.StructureValidator',
    'verapdf': 'ESSArch_Core.fixity.validation.backends.verapdf.VeraPDFValidator',
    'xml_comparison': 'ESSArch_Core.fixity.validation.backends.xml.XMLComparisonValidator',
    'xml_iso_schematron': 'ESSArch_Core.fixity.validation.backends.xml.XMLISOSchematronValidator',
    'xml_schema': 'ESSArch_Core.fixity.validation.backends.xml.XMLSchemaValidator',
    'xml_schematron': 'ESSArch_Core.fixity.validation.backends.xml.XMLSchematronValidator',
    'xml_syntax': 'ESSArch_Core.fixity.validation.backends.xml.XMLSyntaxValidator',
}

extra_validators = getattr(settings, 'ESSARCH_VALIDATORS', {})
AVAILABLE_VALIDATORS.update(extra_validators)

PATH_VARIABLE = "_PATH"


def _validate_file(path, validators, task=None, ip=None, stop_at_failure=True, responsible=None):
    for validator in validators:
        included = False

        if len(validator.include):
            for included_path in validator.include:
                included_path = included_path.format(**validator.data)
                if path in glob(included_path):
                    included = True
                    break
        else:
            included = True

        if len(validator.exclude):
            for excluded_path in validator.exclude:
                excluded_path = excluded_path.format(**validator.data)
                if path in glob(excluded_path):
                    included = False
                    break

        if not included:
            continue

        try:
            validator.data[PATH_VARIABLE] = path
            validator.validate(path)
        except Exception:
            if stop_at_failure:
                raise


def _validate_directory(path, validators, task=None, ip=None, stop_at_failure=True, responsible=None):
    file_validators = [v for v in validators if v.file_validator]
    dir_validators = [v for v in validators if not v.file_validator]

    for validator in dir_validators:
        try:
            validator.data[PATH_VARIABLE] = path
            validator.validate(path)
        except Exception:
            if stop_at_failure:
                raise

    for root, _dirs, files in walk(path):
        for f in files:
            _validate_file(
                os.path.join(root, f),
                file_validators,
                task=task,
                ip=ip,
                stop_at_failure=stop_at_failure,
                responsible=responsible
            )


def validate_path(path, validators, profile, data=None, task=None, ip=None, stop_at_failure=True, responsible=None):
    data = data or {}
    validator_instances = []

    for name in validators:
        try:
            module_name, validator_class = AVAILABLE_VALIDATORS[name].rsplit('.', 1)
        except KeyError:
            raise ValueError('Validator "%s" not found' % name)

        validator = getattr(importlib.import_module(module_name), validator_class)

        for specification in profile.specification.get(name, []):
            required = specification.get('required', True)
            context = specification.get('context')
            include = [os.path.join(path, included) for included in specification.get('include', [])]
            exclude = [os.path.join(path, excluded) for excluded in specification.get('exclude', [])]
            options = specification.get('options', {})

            validator_instance = validator(
                context=context,
                include=include,
                exclude=exclude,
                options=options,
                data=data,
                required=required,
                task=task,
                ip=ip,
                responsible=responsible
            )
            validator_instances.append(validator_instance)

    if os.path.isdir(path):
        _validate_directory(
            path,
            validator_instances,
            task=task,
            ip=ip,
            stop_at_failure=stop_at_failure,
            responsible=responsible
        )

    elif os.path.isfile(path):
        _validate_file(
            path,
            validator_instances,
            task=task,
            ip=ip,
            stop_at_failure=stop_at_failure,
            responsible=responsible
        )

    else:
        raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), path)
