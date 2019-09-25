from pydoc import locate

import click

from ESSArch_Core.config.decorators import initialize
from ESSArch_Core.fixity.validation.exceptions import UnknownValidator


class ValidationCLI(click.MultiCommand):
    @classmethod
    def get_validators(cls):
        from ESSArch_Core.fixity.validation import AVAILABLE_VALIDATORS
        return AVAILABLE_VALIDATORS

    def list_commands(self, ctx):
        return sorted(list(self.get_validators()))

    @initialize
    def get_command(self, ctx, name):
        try:
            validator = locate(self.get_validators()[name])
        except KeyError:
            raise UnknownValidator(name)

        if validator is None:
            raise UnknownValidator(name)

        return validator.cli


@click.command(cls=ValidationCLI)
def validate():
    """Validate files using the specified validator"""
    pass
