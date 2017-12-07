import errno
import importlib
import os

from django.conf import settings
from django.utils import timezone

from glob2 import glob

from scandir import walk

from ESSArch_Core.fixity.models import Validation

AVAILABLE_VALIDATORS = {
    'checksum': 'ESSArch_Core.fixity.validation.backends.checksum.ChecksumValidator',
    'format': 'ESSArch_Core.fixity.validation.backends.format.FormatValidator',
    'mediaconch': 'ESSArch_Core.fixity.validation.backends.mediaconch.MediaconchValidator',
    'structure': 'ESSArch_Core.fixity.validation.backends.structure.StructureValidator',
    'verapdf': 'ESSArch_Core.fixity.validation.backends.verapdf.VeraPDFValidator',
    'xml': 'ESSArch_Core.fixity.validation.backends.xml.XMLValidator',
}

extra_validators = getattr(settings, 'ESSARCH_VALIDATORS', {})
AVAILABLE_VALIDATORS.update(extra_validators)

PATH_VARIABLE = "_PATH"


def _validate_file(path, validators, ip=None, stop_at_failure=True):
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

        obj = Validation.objects.create(
            filename=path,
            time_started=timezone.now(),
            validator=validator.__class__.__name__,
            information_package=ip,
        )
        passed = False

        try:
            validator.data[PATH_VARIABLE] = path
            obj.message = validator.validate(path)
            passed = True
        except Exception as e:
            obj.message = str(e)
            if stop_at_failure:
                raise
        finally:
            if obj.message is None:
                obj.message = ''
            obj.time_done = timezone.now()
            obj.passed = passed
            obj.save(update_fields=['time_done', 'passed', 'message'])


def _validate_directory(path, validators, ip=None, stop_at_failure=True):
    file_validators = [v for v in validators if v.file_validator]
    dir_validators = [v for v in validators if not v.file_validator]

    for validator in dir_validators:
        obj = Validation.objects.create(
            filename=path,
            time_started=timezone.now(),
            validator=validator.__class__.__name__,
            information_package=ip,
        )
        passed = False

        try:
            validator.data[PATH_VARIABLE] = path
            obj.message = validator.validate(path)
            passed = True
        except Exception as e:
            obj.message = str(e)
            if stop_at_failure:
                raise
        finally:
            if obj.message is None:
                obj.message = ''
            obj.time_done = timezone.now()
            obj.passed = passed
            obj.save(update_fields=['time_done', 'passed', 'message'])

    for root, dirs, files in walk(path):
        for f in files:
            _validate_file(os.path.join(root, f), file_validators, ip=ip, stop_at_failure=stop_at_failure)


def validate_path(path, validators, profile, data=None, ip=None, stop_at_failure=True):
    data = data or {}
    validator_instances = []

    for name in validators:
        if name not in AVAILABLE_VALIDATORS.keys():
            raise ValueError('Validator "%s" not specified in profile' % name)

        try:
            module_name, validator_class = AVAILABLE_VALIDATORS[name].rsplit('.', 1)
        except KeyError:
            raise ValueError('Validator "%s" not found' % name)

        validator = getattr(importlib.import_module(module_name), validator_class)

        for specification in profile.specification.get(name, []):
            context = specification.get('context')
            include = [os.path.join(path, included) for included in specification.get('include', [])]
            exclude = [os.path.join(path, excluded) for excluded in specification.get('exclude', [])]
            options = specification.get('options', {})

            validator_instance = validator(context=context, include=include, exclude=exclude, options=options, data=data)
            validator_instances.append(validator_instance)

    if os.path.isdir(path):
        _validate_directory(path, validator_instances, ip=ip, stop_at_failure=stop_at_failure)

    elif os.path.isfile(path):
        _validate_file(path, validator_instances, ip=ip, stop_at_failure=stop_at_failure)

    else:
        raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), path)
