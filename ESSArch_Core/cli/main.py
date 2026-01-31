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
@click.option('--plan', is_flag=True, default=False, help='Do not actually apply migrations.')
def migrate(plan):
    click.secho('Applying database migrations:', fg='green')

    dj_call_command(
        'migrate',
        interactive=False,
        verbosity=1,
        plan=plan,
    )


@cli.command()
@initialize
@click.option('--dry-run', is_flag=True, default=False, help='Do not actually collect static files.')
def collectstatic(dry_run):
    click.secho('Collect static files:', fg='green')

    dj_call_command(
        'collectstatic',
        interactive=False,
        verbosity=1,
        dry_run=dry_run,
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
    ctx.invoke(collectstatic)
    ctx.invoke(migrate)
    _loaddata('countries_data', 'languages_data',)

    from ESSArch_Core.install.install_default_config import (
        installDefaultEventTypes,
        installDefaultFeatures,
        installDefaultParameters,
        installDefaultPaths,
        installDefaultSite,
        installDefaultStorageMethods,
        installDefaultStorageMethodTargetRelations,
        installDefaultStoragePolicies,
        installDefaultStorageTargets,
        installDefaultUsers,
        installPipelines,
        installSearchIndices,
    )
    installDefaultFeatures()
    installDefaultEventTypes()
    installDefaultParameters()
    installDefaultSite()
    installDefaultUsers()
    installDefaultPaths()
    installDefaultStoragePolicies()
    installDefaultStorageMethods()
    installDefaultStorageTargets()
    installDefaultStorageMethodTargetRelations()
    installPipelines()
    installSearchIndices()


@cli.command()
@initialize
@click.option('-q/--quiet', default=False, is_eager=True, expose_value=False, callback=deactivate_prompts)
@click.option('--data-directory', type=click.Path(),
              default=None, help=f'Example: {DEFAULT_DATA_DIR}')
@click.option('--dry-run/--no-dry-run', default=True, help='Run in dry-run mode by default.')
@click.option('--update-existing', is_flag=True, default=False,
              help='Update existing configuration to defaults (requires --no-dry-run).')
@click.option('--remove-extra', is_flag=True, default=False,
              help='Remove extra configuration not part of defaults (requires --no-dry-run).')
@click.option('-y', '--yes', is_flag=True, help='Skip confirmation prompts.')
@click.pass_context
def upgrade(ctx, data_directory, dry_run, update_existing, remove_extra, yes):
    _check()

    if remove_extra and dry_run:
        raise click.UsageError(
            '--remove-extra requires --no-dry-run'
        )

    if not dry_run and not yes:
        click.confirm(
            'This will apply changes to the system. Continue?',
            abort=True,
        )

    if data_directory and not dry_run:
        ctx.invoke(create_data_directories, path=data_directory)

    ctx.invoke(collectstatic, dry_run=dry_run)
    ctx.invoke(migrate, plan=dry_run)
    if not dry_run:
        _loaddata('countries_data', 'languages_data',)

    from ESSArch_Core.install.install_default_config import (
        installDefaultEventTypes,
        installDefaultParameters,
        installDefaultPaths,
        installDefaultRoles,
    )
    installDefaultEventTypes(dry_run=dry_run, update_existing=update_existing, remove_extra=remove_extra)
    installDefaultParameters(dry_run=dry_run, update_existing=update_existing, remove_extra=remove_extra)
    installDefaultPaths(dry_run=dry_run, update_existing=update_existing, remove_extra=remove_extra)
    installDefaultRoles(dry_run=dry_run, remove_extra=remove_extra)


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
            'ESSArch_Core.cli.commands.remote.update_storageMedium',
            'ESSArch_Core.cli.commands.remote.update_storage',
            'ESSArch_Core.cli.commands.remote.update_ip',
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
def storage():
    """Manage storage
    """
    pass


list(
    map(
        lambda cmd: storage.add_command(locate(cmd)), (
            'ESSArch_Core.cli.commands.storage.remove_storage',
            'ESSArch_Core.cli.commands.storage.update_storageMedium',
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
