import os
import string
import unicodedata

from ESSArch_Core.fixity.transformation.backends.base import BaseTransformer

DEFAULT_WHITELIST = "-_. %s%s" % (string.ascii_letters, string.digits)


class FilenameTransformer(BaseTransformer):
    @staticmethod
    def clean(filename, whitelist=DEFAULT_WHITELIST, replace=None, normalize_unicode=True):
        if replace is None:
            replace = {' ': '_'}

        for k, v in replace.items():
            filename = filename.replace(k, v)

        if normalize_unicode:
            # keep only valid ascii chars
            filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode()

        # keep only whitelisted chars
        return ''.join(c for c in filename if c in whitelist)

    def transform(self, path, whitelist=DEFAULT_WHITELIST, replace=None, normalize_unicode=True):
        new_path = self.clean(path, whitelist, replace, normalize_unicode)
        os.rename(path, new_path)
