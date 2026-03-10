from pydoc import locate

import click
from django.conf import settings

from ESSArch_Core.config.decorators import initialize
from ESSArch_Core.search import alias_migration


@initialize
def import_globally():
    global Structure
    from ESSArch_Core.tags.models import Structure


def get_indexes(indexes):
    all_indexes = getattr(settings, 'ELASTICSEARCH_INDEXES', {'default': {}})['default']

    if indexes:
        indexes = {key: all_indexes[key] for key in indexes}
    else:
        indexes = all_indexes

    return [locate(cls) for name, cls in indexes.items()]


@click.command()
@click.option('-i', '--index', 'indexes', type=str, multiple=True, help='Specify which index to update.')
@initialize
def clear(indexes):
    """Clear indices
    """

    indexes = get_indexes(indexes)

    for index in indexes:
        click.secho('Clearing {}... '.format(index._index._name), nl=False)
        clear_index(index)
        click.secho('done', fg='green')


@click.command()
@click.option('-i', '--index', 'indexes', type=str, multiple=True, help='Specify which index to update. \
(agent, archive, component, directory, document, information_package, structure_unit)')
@click.option('-b', '--batch-size', 'batch_size', type=int, help='Number of items to index at once.')
@click.option('-r', '--remove-stale', 'remove_stale', is_flag=True, default=False, help='Remove objects from the \
index that are no longer in the database.')
@click.option('--do-not-delete-old-index', 'do_not_delete_old', is_flag=True, default=False, help='Skip to clear old \
index. Importent for document index (File) if you do not want to rebuild index from files.')
@click.option('--index-file-content', 'index_file_content', is_flag=True, default=False, help='Rebuild index from \
files for document index (File) "field - attachment".')
@initialize
def rebuild(indexes, batch_size, remove_stale, do_not_delete_old, index_file_content):
    """Rebuild indices
    """

    indexes = get_indexes(indexes)

    for index in indexes:
        if not do_not_delete_old:
            click.secho('Clear old index {}... '.format(index._index._name), nl=False)
            clear_index(index)
            click.secho('done', fg='green')
        click.secho('Rebuilding {}... '.format(index._index._name), nl=False)
        index_documents(index, batch_size, remove_stale, index_file_content)
        click.secho('done', fg='green')


@click.command()
@click.option('-i', '--index', 'indexes', type=str, multiple=True, help='Specify which index to update. \
                    (agent, archive, component, directory, document, information_package, structure_unit)')
@click.option('-m', '--move-data', 'move_data', is_flag=True, default=True)
@click.option('-u', '--update-alias', 'update_alias', is_flag=True, default=True)
@click.option('-d', '--delete-old-index', 'delete_old', is_flag=True, default=False)
@initialize
def migrate(indexes, move_data, update_alias, delete_old):
    """Migrate indices
    """

    indexes = get_indexes(indexes)

    for index in indexes:
        click.secho('Migrating {}... '.format(index._index._name), nl=False)
        alias_migration.migrate(index, move_data=move_data, update_alias=update_alias, delete_old_index=delete_old)
        click.secho('done', fg='green')


def clear_index(index):
    index.clear_index()


def index_documents(index, batch_size, remove_stale, index_file_content=False):
    index.index_documents(batch_size, remove_stale, index_file_content)


@click.command()
@click.option('--template-id', type=str, help="Delete all structures belonging to this template UUID")
@click.option('--structure-id', type=str, help="Delete a specific structure UUID")
@click.option('--dry-run', is_flag=True, help="Show what would be deleted without actually deleting")
@click.option('-y', '--yes', is_flag=True, help="Skip confirmation prompt")
@initialize
def delete_structures(template_id, structure_id, dry_run, yes):
    """
    Delete Structure objects and their related tagstructures.
    """
    import_globally()

    # Validate options
    if template_id and structure_id:
        raise click.UsageError("Use only ONE of --template-id or --structure-id")

    if not template_id and not structure_id:
        raise click.UsageError("You must provide either --template-id or --structure-id")

    # Query structures
    if template_id:
        structures = Structure.objects.filter(template_id=template_id)

    elif structure_id:
        structures = Structure.objects.filter(id=structure_id)

    count = structures.count()

    if count == 0:
        click.echo("No structures found.")
        return

    click.echo(f"{count} structure(s) will be affected.")

    if dry_run:
        click.echo("DRY RUN MODE")
        for s in structures:
            click.echo(f"Would delete structure {s}")
            for ts in s.tagstructure_set.all():
                click.echo(f"  Would delete related tagstructure {ts}")
        return

    if not yes:
        click.confirm("Are you sure you want to delete these structures?", abort=True)

    for structure in structures:
        tag_count = structure.tagstructure_set.count()

        click.echo(f"Deleting structure {structure.id} with {tag_count} tagstructure(s)")

        structure.tagstructure_set.all().delete()
        structure.delete()

    click.echo("Done.")
