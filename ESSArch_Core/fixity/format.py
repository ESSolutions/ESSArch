import logging
import mimetypes
import os
import time

from django.conf import settings
from fido.fido import Fido
from fido.versions import get_local_versions

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.exceptions import (
    EncryptedFileNotAllowed,
    FileFormatNotAllowed,
)
from ESSArch_Core.fixity.validation.backends.encryption import (
    FileEncryptionValidator,
)

MB = 1024 * 1024
DEFAULT_MIMETYPE = 'application/octet-stream'


class FormatIdentifier:
    _fido = None

    def __init__(self, allow_unknown_file_types=False, allow_encrypted_files=False,
                 use_fido_pronom_formats=True, use_fido_extension_formats=True,
                 use_ess_formats=True):
        self.allow_unknown_file_types = allow_unknown_file_types
        self.allow_encrypted_files = allow_encrypted_files
        self.use_fido_pronom_formats = use_fido_pronom_formats
        self.use_fido_extension_formats = use_fido_extension_formats
        self.use_ess_formats = use_ess_formats

    @property
    def fido(self):
        logger = logging.getLogger('essarch.fixity.format')
        if self._fido is None:
            logger.debug('Initiating fido')
            format_files = []
            if self.use_fido_pronom_formats or self.use_fido_extension_formats:
                versions = get_local_versions()
                format_files.append(versions.pronom_signature) if self.use_fido_pronom_formats else None
                format_files.append(versions.fido_extension_signature) if self.use_fido_extension_formats else None

            self._fido = Fido(
                handle_matches=self.handle_matches,
                nocontainer=True,
                format_files=format_files,
            )
            if self.use_ess_formats:
                config_dir = settings.CONFIG_DIR
                try:
                    self._fido.load_fido_xml(os.path.join(config_dir, 'file_formats.xml'))
                except FileNotFoundError as e:
                    logger.warning('FIDO missing local formats configuration. Error: {}'.format(e))

            logger.info('Initiated fido')
        return self._fido

    def _init_mimetypes(self):
        logger = logging.getLogger('essarch.fixity.format')
        try:
            mimetypes_file = Path.objects.get(
                entity="mimetypes_definitionfile"
            ).value
            if os.path.isfile(mimetypes_file):
                logger.debug('Initiating mimetypes from %s' % mimetypes_file)
                mime = mimetypes.MimeTypes()
                mime.suffix_map = {}
                mime.encodings_map = {}
                mime.types_map = ({}, {})
                mime.types_map_inv = ({}, {})
                mime.read(mimetypes_file)
                logger.info('Initiated mimetypes from %s' % mimetypes_file)
                return mime
            else:
                logger.debug('Custom mimetypes file %s does not exist' % mimetypes_file)
        except Path.DoesNotExist:
            logger.debug('No custom mimetypes file specified')

        logger.debug('Initiating default mimetypes')
        mime = mimetypes.MimeTypes()
        logger.info('Initiated default mimetypes')
        return mime

    def get_mimetype(self, fname):
        logger = logging.getLogger('essarch.fixity.format')
        logger.debug('Getting mimetype for %s' % fname)
        mime = self._init_mimetypes()

        content_type, encoding = mime.guess_type(fname)
        logger.info('Guessed mimetype for %s: type: %s, encoding: %s' % (fname, content_type, encoding))

        if content_type is None:
            if self.allow_unknown_file_types:
                logger.info('Got mimetype %s setting to %s for %s' % (content_type, DEFAULT_MIMETYPE, fname))
                return DEFAULT_MIMETYPE

            raise FileFormatNotAllowed("Extension of '%s' is missing from mimetypes and is not allowed" % fname)

        encoding_map = {
            'bzip2': 'application/x-bzip',
            'gzip': 'application/gzip',
            'xz': 'application/x-xz',
        }

        # We skip setting Content-Encoding inorder to prevent browsers from
        # automatically uncompressing files. Instead we set the Content-Type to
        # the encoded mimetype
        mtype = encoding_map.get(encoding, content_type)
        logger.info('Got mimetype %s for %s' % (mtype, fname))
        return mtype

    def handle_matches(self, fullname, matches, delta_t, matchtype=''):
        if len(matches) == 0:
            if self.allow_unknown_file_types:
                self.format_name = 'Unknown File Format'
                self.format_version = None
                self.format_registry_key = None
                return

            raise ValueError("No matches for %s" % fullname)

        f, _ = matches[-1]

        try:
            self.format_name = f.find('name').text
        except AttributeError:
            self.format_name = None

        try:
            self.format_version = f.find('version').text
        except AttributeError:
            self.format_version = None

        try:
            self.format_registry_key = f.find('puid').text
        except AttributeError:
            self.format_registry_key = None

    def identify_file_encryption(self, filename):
        try:
            encrypted = FileEncryptionValidator.is_file_encrypted(filename) or False
        except Exception:
            encrypted = False

        if encrypted and not self.allow_encrypted_files:
            raise EncryptedFileNotAllowed(
                "{} is encrypted and therefore not allowed".format(filename)
            )
        return encrypted

    def identify_file_format(self, filename):
        """
        Identifies the format of the file using the fido library

        Args:
            filename: The filename to identify

        Returns:
            A tuple with the format name, version and registry key
        """

        logger = logging.getLogger('essarch.fixity.format')
        if os.name == 'nt':
            start_time = time.perf_counter()
        else:
            start_time = time.time()

        logger.debug("Identifying file format of %s ..." % (filename,))

        self.fido.identify_file(filename)

        if os.name == 'nt':
            end_time = time.perf_counter()
        else:
            end_time = time.time()

        time_elapsed = end_time - start_time
        size = os.path.getsize(filename)
        size_mb = size / MB
        try:
            mb_per_sec = size_mb / time_elapsed
        except ZeroDivisionError:
            mb_per_sec = size_mb

        file_format = (self.format_name, self.format_version, self.format_registry_key)
        from ESSArch_Core.util import pretty_mb_per_sec, pretty_time_to_sec
        logger.info(
            "Identified the format of %s at %s MB/Sec (%s sec): %s" % (
                filename, pretty_mb_per_sec(mb_per_sec), pretty_time_to_sec(time_elapsed), file_format
            )
        )

        return file_format
