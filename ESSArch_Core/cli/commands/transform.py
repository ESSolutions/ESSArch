from pydoc import locate

import click

from ESSArch_Core.config.decorators import initialize


class TransformationCLI(click.MultiCommand):
    @classmethod
    def get_transformers(cls):
        from ESSArch_Core.fixity.transformation import AVAILABLE_TRANSFORMERS
        return AVAILABLE_TRANSFORMERS

    def list_commands(self, ctx):
        return sorted(list(self.get_transformers()))

    @initialize
    def get_command(self, ctx, name):
        from ESSArch_Core.fixity.transformation.exceptions import UnknownTransformer

        try:
            transformer = locate(self.get_transformers()[name])
        except KeyError:
            raise UnknownTransformer(name)

        if transformer is None:
            raise UnknownTransformer(name)

        return transformer.cli


@click.command(cls=TransformationCLI)
def transform():
    """Transform files using the specified transformer"""
    pass
