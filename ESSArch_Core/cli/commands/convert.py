from pydoc import locate

import click


class ConversionCLI(click.MultiCommand):
    @classmethod
    def get_converters(cls):
        from ESSArch_Core.fixity.conversion import AVAILABLE_CONVERTERS
        return AVAILABLE_CONVERTERS

    def list_commands(self, ctx):
        return sorted(list(self.get_converters()))

    def get_command(self, ctx, name):
        return locate(self.get_converters()[name]).cli


@click.command(cls=ConversionCLI)
def convert():
    """Convert files using the specified converter"""
    pass
