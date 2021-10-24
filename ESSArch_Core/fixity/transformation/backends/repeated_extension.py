import os
import re

import click

from ESSArch_Core.fixity.transformation.backends.base import BaseTransformer

REPEATED_PATTERN = r'\.(\w+)(\.(\1))+'


class RepeatedExtensionTransformer(BaseTransformer):
    @classmethod
    def transform(cls, path):
        """
        Normalizes file extensions by removing repeated extensions.
        e.g. foo.bar.bar will be renamed to foo.bar but foo.bar.baz will not be altered

        Args:
            path: The file to normalize

        """
        new_path = re.sub(REPEATED_PATTERN, '.\\1', path)
        os.rename(path, new_path)

    @staticmethod
    @click.command()
    @click.argument('path', metavar='INPUT', type=click.Path(exists=True))
    def cli(path):
        RepeatedExtensionTransformer.transform(path)
