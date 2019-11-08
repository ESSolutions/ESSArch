from pydoc import locate

import click

from ESSArch_Core.config.decorators import initialize


class ConversionCLI(click.MultiCommand):
    @classmethod
    def get_converters(cls):
        from ESSArch_Core.fixity.conversion import AVAILABLE_CONVERTERS
        return AVAILABLE_CONVERTERS

    def list_commands(self, ctx):
        return sorted(list(self.get_converters()))

    @initialize
    def get_command(self, ctx, name):
        from ESSArch_Core.fixity.conversion.exceptions import UnknownConverter

        try:
            converter = locate(self.get_converters()[name])
        except KeyError:
            raise UnknownConverter(name)

        if converter is None:
            raise UnknownConverter(name)

        return converter.cli


@click.command(cls=ConversionCLI)
def convert():
    """Convert files using the specified converter"""
    pass
