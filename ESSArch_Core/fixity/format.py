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


class FormatIdentifier:
    def __init__(self, allow_unknown_file_types=False):
        self.fido = Fido(handle_matches=self.handle_matches)
        self.allow_unknown_file_types = allow_unknown_file_types

        mimetypes.suffix_map = {}
        mimetypes.encodings_map = {}
        mimetypes.types_map = {}
        mimetypes.common_types = {}
        mimetypes_file = Path.objects.get(
            entity="path_mimetypes_definitionfile"
        ).value
        mimetypes.init(files=[mimetypes_file])
        self.mimetypes = mimetypes.types_map

    def get_mimetype(self, fname):
        file_name, file_ext = os.path.splitext(fname)

        if not file_ext:
            file_ext = file_name

        try:
            return self.mimetypes[file_ext.lower()]
        except KeyError:
            if self.allow_unknown_file_types:
                return 'application/octet-stream'

            raise FileFormatNotAllowed("Extension of '%s' is missing from mimetypes and is not allowed" % fname)

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
