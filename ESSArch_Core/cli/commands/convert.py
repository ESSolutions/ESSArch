from pydoc import locate

import click

from ESSArch_Core.fixity.conversion import AVAILABLE_CONVERTERS


class ConversionCLI(click.MultiCommand):
    def list_commands(self, ctx):
        return sorted(list(AVAILABLE_CONVERTERS))

    def get_command(self, ctx, name):
        return locate(AVAILABLE_CONVERTERS[name]).cli


@click.command(cls=ConversionCLI)
def convert():
    """Convert files using the specified converter"""
    pass
