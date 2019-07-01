from pydoc import locate

import click


class TransformationCLI(click.MultiCommand):
    @classmethod
    def get_transformers(cls):
        from ESSArch_Core.fixity.transformation import AVAILABLE_TRANSFORMERS
        return AVAILABLE_TRANSFORMERS

    def list_commands(self, ctx):
        return sorted(list(self.get_transformers()))

    def get_command(self, ctx, name):
        return locate(self.get_transformers()[name]).cli


@click.command(cls=TransformationCLI)
def transform():
    """Transform files using the specified transformer"""
    pass
