from pydoc import locate

import click

from ESSArch_Core.config.decorators import initialize


class ValidationCLI(click.MultiCommand):
    @classmethod
    def get_validators(cls):
        from ESSArch_Core.fixity.validation import AVAILABLE_VALIDATORS
        return AVAILABLE_VALIDATORS

    def list_commands(self, ctx):
        return sorted(list(self.get_validators()))

    @initialize
    def get_command(self, ctx, name):
        return locate(self.get_validators()[name]).cli


@click.command(cls=ValidationCLI)
def validate():
    """Validate files using the specified validator"""
    pass
