import os
import string
import unicodedata

import click

from ESSArch_Core.fixity.transformation.backends.base import BaseTransformer

DEFAULT_WHITELIST_FILE = "-_. %s%s" % (string.ascii_letters, string.digits)
DEFAULT_WHITELIST_DIR = "-_ %s%s" % (string.ascii_letters, string.digits)


class FilenameTransformer(BaseTransformer):
    @staticmethod
    def clean(filename, whitelist, replace=None, normalize_unicode=True):
        if replace is None:
            replace = {}

        for k, v in replace.items():
            filename = filename.replace(k, v)

        if normalize_unicode:
            # keep only valid ascii chars
            filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode()

        # keep only whitelisted chars
        return ''.join(c for c in filename if c in whitelist)

    @classmethod
    def transform(cls, path, whitelist=None, replace=None, normalize_unicode=True):

        if whitelist is None:
            if os.path.isfile(path):
                whitelist = DEFAULT_WHITELIST_FILE
            else:
                whitelist = DEFAULT_WHITELIST_DIR

        if replace is None:
            replace = {' ': '_'}

            if os.path.isdir(path):
                replace['.'] = '_'

        basename = os.path.basename(path)
        new_basename = cls.clean(basename, whitelist, replace, normalize_unicode)
        os.rename(path, os.path.join(os.path.dirname(path), new_basename))

    @staticmethod
    @click.command()
    @click.argument('path', metavar='INPUT', type=click.Path(exists=True))
    @click.option('--whitelist')
    @click.option('-r', '--replace', type=(str, str), multiple=True)
    @click.option('--normalize-unicode/--no-normalize-unicode', default=True)
    def cli(path, whitelist, replace, normalize_unicode):
        replace = {k: v for k, v in replace}
        FilenameTransformer.transform(path, whitelist, replace, normalize_unicode)
