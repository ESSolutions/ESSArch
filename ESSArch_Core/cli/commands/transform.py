from pydoc import locate

import click

from ESSArch_Core.fixity.transformation import AVAILABLE_TRANSFORMERS


class TransformationCLI(click.MultiCommand):
    def list_commands(self, ctx):
        return sorted(list(AVAILABLE_TRANSFORMERS))

    def get_command(self, ctx, name):
        return locate(AVAILABLE_TRANSFORMERS[name]).cli


@click.command(cls=TransformationCLI)
def transform():
    """Transform files using the specified transformer"""
    pass
