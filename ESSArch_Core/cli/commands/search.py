from pydoc import locate

import click
from django.conf import settings

from ESSArch_Core.config.decorators import initialize
from ESSArch_Core.search import alias_migration


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
