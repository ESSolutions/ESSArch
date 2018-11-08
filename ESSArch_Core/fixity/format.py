from __future__ import division, unicode_literals

import logging
import mimetypes
import os
import time

from fido.fido import Fido

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.exceptions import FileFormatNotAllowed

MB = 1024*1024

logger = logging.getLogger('essarch.fixity.format')

DEFAULT_MIMETYPE = 'application/octet-stream'


class FormatIdentifier:
    _fido = None
    _mimetypes = None

    def __init__(self, allow_unknown_file_types=False):
        self.allow_unknown_file_types = allow_unknown_file_types

    @property
    def fido(self):
        if self._fido is None:
            self._fido = Fido(handle_matches=self.handle_matches)
        return self._fido

    def _init_mimetypes(self):
        try:
            mimetypes_file = Path.objects.get(
                entity="path_mimetypes_definitionfile"
            ).value
            if mimetypes_file:
                mimetypes.suffix_map = {}
                mimetypes.encodings_map = {}
                mimetypes.types_map = {}
                mimetypes.common_types = {}
                mimetypes.init(files=[mimetypes_file])
                return
        except Path.DoesNotExist:
            pass

        mimetypes.init()
        mimetypes._default_mime_types()

    def get_mimetype(self, fname):
        self._init_mimetypes()
        file_name, file_ext = os.path.splitext(fname)

        if not file_ext:
            file_ext = file_name

        content_type, encoding = mimetypes.guess_type(fname)
        if content_type is None:
            if self.allow_unknown_file_types:
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
        return encoding_map.get(encoding, content_type)

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

    def identify_file_format(self, filename):
        """
        Identifies the format of the file using the fido library

        Args:
            filename: The filename to identify

        Returns:
            A tuple with the format name, version and registry key
        """


        if os.name == 'nt':
                start_time = time.clock()
        else:
                start_time = time.time()

        logger.debug("Identifying file format of %s ..." % (filename,))

        self.fido.identify_file(filename)

        if os.name == 'nt':
                end_time = time.clock()
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
        logger.info("Identified the format of %s at %s MB/Sec (%s sec): %s" % (filename, mb_per_sec, time_elapsed, file_format))

        return file_format
