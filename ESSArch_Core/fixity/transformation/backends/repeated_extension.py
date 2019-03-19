import os
import re

import click

from ESSArch_Core.fixity.transformation.backends.base import BaseTransformer

REPEATED_PATTERN = r'\.(\w+)(\.(\1))+'


class RepeatedExtensionTransformer(BaseTransformer):
    @classmethod
    def transform(cls, path):
        new_path = re.sub(REPEATED_PATTERN, '.\\1', path)
        os.rename(path, new_path)

    @staticmethod
    @click.command()
    @click.argument('path', metavar='INPUT', type=click.Path(exists=True))
    def cli(path):
        RepeatedExtensionTransformer.transform(path)
