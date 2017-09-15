import logging
import mimetypes

from fido.fido import Fido

from ESSArch_Core.configuration.models import Path

logger = logging.getLogger('essarch.fixity.format')


class FormatIdentifier:
    def __init__(self):
        self.fido = Fido(handle_matches=self.handle_matches)

        mimetypes.suffix_map = {}
        mimetypes.encodings_map = {}
        mimetypes.types_map = {}
        mimetypes.common_types = {}
        mimetypes_file = Path.objects.get(
            entity="path_mimetypes_definitionfile"
        ).value
        mimetypes.init(files=[mimetypes_file])
        self.mimetypes = mimetypes.types_map

    def handle_matches(self, fullname, matches, delta_t, matchtype=''):
        if len(matches) == 0:
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

        logger.info("Identifying the format of %s" % filename)
        self.fido.identify_file(filename)
        file_format = (self.format_name, self.format_version, self.format_registry_key)
        logger.info("Identified the format of %s: %s" % (filename, file_format))

        return file_format
