from pydoc import locate

import click
from django.conf import settings


def get_indexes(indexes):
    all_indexes = getattr(settings, 'ELASTICSEARCH_INDEXES', {'default': {}})['default']

    if indexes:
        indexes = {key: all_indexes[key] for key in indexes}
    else:
        indexes = all_indexes

    return [locate(cls) for name, cls in indexes.items()]


@click.command()
@click.option('-i', '--index', 'indexes', type=str, multiple=True, help='Specify which index to update.')
def clear(indexes):
    """Clear indices
    """

    indexes = get_indexes(indexes)

    for index in indexes:
        clear_index(index)


@click.command()
@click.option('-i', '--index', 'indexes', type=str, multiple=True, help='Specify which index to update.')
@click.option('-b', '--batch-size', 'batch_size', type=int, help='Number of items to index at once.')
@click.option('-r', '--remove-stale', 'remove_stale', default=False, help='Remove objects from the index \
                                                                           that are no longer in the database.')
def rebuild(indexes, batch_size, remove_stale):
    """Rebuild indices
    """

    indexes = get_indexes(indexes)

    for index in indexes:
        clear_index(index)
        index_documents(index, batch_size, remove_stale)


def clear_index(index):
    index.clear_index()


def index_documents(index, batch_size, remove_stale):
    index.index_documents(batch_size, remove_stale)
