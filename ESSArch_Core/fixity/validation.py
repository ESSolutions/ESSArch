import logging

from django.utils import timezone

from .checksum import calculate_checksum
from .mediaconch import validate_file as mediaconch_validation

logger = logging.getLogger('essarch.fixity.validation')


def validate_checksum(filename, algorithm, checksum, block_size=65536):
    logger.info('Validating checksum of %s' % filename)

    checksum = checksum.lower()
    actual_checksum = calculate_checksum(filename, algorithm=algorithm, block_size=block_size)
    assert actual_checksum == checksum, "checksum for %s is not valid (%s != %s)" % (filename, checksum, actual_checksum)

    logger.info('Successfully validated checksum of %s' % filename)


def validate_file_format(filename, fid, format_name=None, format_version=None, format_registry_key=None):
    if not any(f is not None for f in (format_name, format_version, format_registry_key)):
        raise ValueError('At least one of name, version and registry key is required')

    logger.info('Validating format of %s' % filename)

    actual_format_name, actual_format_version, actual_format_registry_key = fid.identify_file_format(filename)

    if format_name:
        logger.error('Invalid format name of %s, %s != %s' % (filename, format_name, actual_format_name))
        assert actual_format_name == format_name, "format name for %s is not valid, (%s != %s)" % (filename, format_name, actual_format_name)

    if format_version:
        logger.error('Invalid format version of %s, %s != %s' % (filename, format_version, actual_format_version))
        assert actual_format_version == format_version, "format version for %s is not valid" % filename

    if format_registry_key:
        logger.error('Invalid format registry key of %s, %s != %s' % (filename, format_registry_key, actual_format_registry_key))
        assert actual_format_registry_key == format_registry_key, "format registry key for %s is not valid" % filename

    logger.info('Successfully validated format of %s' % filename)


def validate_mediaconch(filename, policy=None):
    passed, message = mediaconch_validation(filename, policy)

    if not passed:
        raise AssertionError(message)
