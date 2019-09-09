import os
import sys
from pydoc import locate

import click
from django.core.management import call_command as dj_call_command

from ESSArch_Core.cli import deactivate_prompts
from ESSArch_Core.config.decorators import initialize

LOG_LEVELS = ('DEBUG', 'INFO', 'WARNING', 'WARN', 'ERROR', 'CRITICAL', 'FATAL')
DEFAULT_DATA_DIR = '/ESSArch/data'


@click.group()
@click.pass_context
def cli(ctx):
    """ESSArch is an open source archival solution
    compliant to the OAIS ISO-standard
    """

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ESSArch_Core.config.settings')


def _loaddata(*fixture_labels):
    dj_call_command(
        'loaddata',
        *fixture_labels,
    )


@cli.command()
@initialize
def migrate():
    click.secho('Applying database migrations:', fg='green')

    dj_call_command(
        'migrate',
        interactive=False,
        verbosity=1,
    )


@cli.command()
@click.option('-q/--quiet', default=False, is_eager=True, expose_value=False, callback=deactivate_prompts)
@click.option('-p', '--path', type=click.Path(),
              default=DEFAULT_DATA_DIR, show_default=DEFAULT_DATA_DIR)
def create_data_directories(path):
    dirs = [
        'etp/prepare',
        'etp/prepare_reception',
        'etp/reception',
        'gate/reception',
        'epp/ingest',
        'epp/cache',
        'epp/work',
        'epp/disseminations',
        'epp/orders',
        'epp/verify',
        'epp/temp',
        'epp/reports/appraisal',
        'epp/reports/conversion',
        'eta/reception/eft',
        'eta/uip',
        'eta/work',
        'receipts/xml',
        'store/cache',
        'store/disk1',
        'store/longterm_disk1',
    ]

    click.secho('Creating data directories:', fg='green')
    for d in dirs:
        full_path = os.path.join(path, d)
        click.echo(' - %s' % full_path)
        os.makedirs(full_path, exist_ok=True)


@cli.command()
@click.option('-q/--quiet', default=False, is_eager=True, expose_value=False, callback=deactivate_prompts)
@click.option('--data-directory', type=click.Path(),
              default=DEFAULT_DATA_DIR, show_default=DEFAULT_DATA_DIR)
@click.pass_context
def install(ctx, data_directory):
    # verify that a local settings file has been created
    try:
        import local_essarch_settings  # noqa isort:skip
    except ImportError:
        exit('No settings file found, create one by running `essarch settings generate`')

    if data_directory is None:
        data_directory = click.prompt('Data directory', default='/ESSArch/data', type=click.Path())
    ctx.invoke(create_data_directories, path=data_directory)
    ctx.invoke(migrate)
    _loaddata('countries_data', 'languages_data',)


@click.option('-l', '--loglevel', default='INFO', type=click.Choice(LOG_LEVELS, case_sensitive=False))
@click.option('-c', '--concurrency', default=None, type=int)
@click.option('-q', '--queues', default='celery,file_operation,validation')
@cli.command()
@initialize
def worker(queues, concurrency, loglevel):
    from ESSArch_Core.config.celery import app

    worker = app.Worker(
        loglevel=loglevel,
        concurrency=concurrency,
        queues=queues,
        optimization='fair',
        prefetch_multiplier=1,
    )
    worker.start()
    sys.exit(worker.exitcode)


@click.option('-l', '--loglevel', default='INFO', type=click.Choice(LOG_LEVELS, case_sensitive=False))
@cli.command()
@initialize
def beat(loglevel):
    from ESSArch_Core.config.celery import app
    app.Beat(loglevel=loglevel).run()


list(
    map(
        lambda cmd: cli.add_command(locate(cmd)), (
            'ESSArch_Core.cli.commands.convert.convert',
            'ESSArch_Core.cli.commands.transform.transform',
            'ESSArch_Core.cli.commands.validate.validate',
        )
    )
)


@cli.group()
def search():
    """Manage search indices
    """
    pass


list(
    map(
        lambda cmd: search.add_command(locate(cmd)), (
            'ESSArch_Core.cli.commands.search.clear',
            'ESSArch_Core.cli.commands.search.migrate',
            'ESSArch_Core.cli.commands.search.rebuild',
        )
    )
)


@cli.group()
def settings():
    """Manage settings
    """
    pass


list(
    map(
        lambda cmd: settings.add_command(locate(cmd)), (
            'ESSArch_Core.cli.commands.settings.generate',
        )
    )
)
