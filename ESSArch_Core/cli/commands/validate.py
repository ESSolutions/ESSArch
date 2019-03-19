from pydoc import locate

import click

from ESSArch_Core.fixity.validation import AVAILABLE_VALIDATORS


class ValidationCLI(click.MultiCommand):
    def list_commands(self, ctx):
        return sorted(list(AVAILABLE_VALIDATORS))

    def get_command(self, ctx, name):
        return locate(AVAILABLE_VALIDATORS[name]).cli


@click.command(cls=ValidationCLI)
def validate():
    """Validate files using the specified validator"""
    pass
