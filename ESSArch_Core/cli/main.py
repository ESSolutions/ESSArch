from pydoc import locate

import click
import django
django.setup()
from django.core.management import call_command as dj_call_command


def _migrate(interactive, verbosity):
    dj_call_command(
        'migrate',
        interactive=interactive,
        verbosity=verbosity,
    )


@click.group()
@click.pass_context
def cli(ctx):
    """ESSArch is an open source archival solution
    compliant to the OAIS ISO-standard
    """


@cli.group()
def search():
    """Manage search indices
    """
    pass


list(
    map(
        lambda cmd: search.add_command(locate(cmd)), (
            'ESSArch_Core.cli.commands.search.clear',
            'ESSArch_Core.cli.commands.search.rebuild',
        )
    )
)
