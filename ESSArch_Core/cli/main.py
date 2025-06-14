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


def _check():
    try:
        dj_call_command(
            'check',
        )
    except Exception as e:
        exit(e)


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
@click.argument('addrport', default='127.0.0.1:8000', type=str)
@click.option('--noreload', default=False, is_flag=True, help='Tells Django to NOT use the auto-reloader.')
@initialize
def devserver(addrport, noreload):
    dj_call_command(
        'runserver',
        addrport=addrport,
        use_reloader=not noreload,
    )


@cli.command()
@click.option('-q/--quiet', default=False, is_eager=True, expose_value=False, callback=deactivate_prompts)
@click.option('-p', '--path', type=click.Path(),
              default=DEFAULT_DATA_DIR, show_default=DEFAULT_DATA_DIR)
def create_data_directories(path):
    dirs = [
        'access',
        'disseminations',
        'ingest/packages',
        'ingest/reception',
        'ingest/transfer',
        'ingest/uip',
        'orders',
        'preingest/packages',
        'preingest/reception',
        'receipts/xml',
        'reports/appraisal',
        'reports/conversion',
        'store/cache',
        'store/disk1',
        'store/longterm_disk1',
        'temp',
        'verify',
        'workspace',
    ]

    click.secho('Creating data directories:', fg='green')
    for d in dirs:
        full_path = os.path.join(path, d)
        click.echo(' - %s' % full_path)
        os.makedirs(full_path, exist_ok=True)


@cli.command()
@initialize
@click.option('-q/--quiet', default=False, is_eager=True, expose_value=False, callback=deactivate_prompts)
@click.option('--data-directory', type=click.Path(),
              default=DEFAULT_DATA_DIR, show_default=DEFAULT_DATA_DIR)
@click.pass_context
def install(ctx, data_directory):
    _check()
    if data_directory is None:
        data_directory = click.prompt('Data directory', default='/ESSArch/data', type=click.Path())
    ctx.invoke(create_data_directories, path=data_directory)
    ctx.invoke(migrate)
    _loaddata('countries_data', 'languages_data',)

    from ESSArch_Core.install.install_default_config import (
        installDefaultConfiguration,
    )
    installDefaultConfiguration()


@click.option('-P', '--pool', default='prefork',
              type=click.Choice(('prefork', 'eventlet', 'gevent', 'threads', 'solo'), case_sensitive=False))
@click.option('--pidfile', default=None, type=click.Path(exists=False, file_okay=True, dir_okay=False))
@click.option('-f', '--logfile', default=None, type=click.Path(exists=False, file_okay=True, dir_okay=False))
@click.option('-l', '--loglevel', default='INFO', type=click.Choice(LOG_LEVELS, case_sensitive=False))
@click.option('-n', '--hostname', default=None)
@click.option('-c', '--concurrency', default=None, type=int)
@click.option('-Q', '--queues', default='celery,file_operation,validation')
@cli.command()
@initialize
def worker(queues, concurrency, hostname, loglevel, logfile, pidfile, pool):
    from ESSArch_Core.config.celery import app

    worker = app.Worker(
        logfile=logfile,
        loglevel=loglevel,
        concurrency=concurrency,
        queues=queues,
        optimization='fair',
        prefetch_multiplier=1,
        hostname=hostname,
        pidfile=pidfile,
        pool=pool,
    )
    worker.start()
    sys.exit(worker.exitcode)


@click.option('--pidfile', default=None, type=click.Path(exists=False, file_okay=True, dir_okay=False))
@click.option('-f', '--logfile', default=None, type=click.Path(exists=False, file_okay=True, dir_okay=False))
@click.option('-l', '--loglevel', default='INFO', type=click.Choice(LOG_LEVELS, case_sensitive=False))
@click.option('-s', '--schedule', default=None, type=click.Path(exists=False, file_okay=True, dir_okay=False))
@cli.command()
@initialize
def beat(loglevel, logfile, pidfile, schedule):
    from ESSArch_Core.config.celery import app
    app.Beat(
        logfile=logfile,
        loglevel=loglevel,
        pidfile=pidfile,
        schedule=schedule,
    ).run()


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
def remote():
    """Manage remote
    """
    pass


list(
    map(
        lambda cmd: remote.add_command(locate(cmd)), (
            'ESSArch_Core.cli.commands.remote.update_sa',
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


@cli.group()
def system():
    """System Information
    """
    pass


list(
    map(
        lambda cmd: system.add_command(locate(cmd)), (
            'ESSArch_Core.cli.commands.system.version',
        )
    )
)


@cli.group()
def mimetypes():
    """Manage mime.types
    """
    pass


list(
    map(
        lambda cmd: mimetypes.add_command(locate(cmd)), (
            'ESSArch_Core.cli.commands.mimetypes.generate',
        )
    )
)


@cli.group()
def workflow():
    """Manage workflow
    """
    pass


list(
    map(
        lambda cmd: workflow.add_command(locate(cmd)), (
            'ESSArch_Core.cli.commands.workflow.remove_step',
            'ESSArch_Core.cli.commands.workflow.revoke_task',
        )
    )
)
