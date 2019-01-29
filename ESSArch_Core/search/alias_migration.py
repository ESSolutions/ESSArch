"""
Methods for updating the mapping of a doctype by reindexing and updating the alias

https://github.com/elastic/elasticsearch-dsl-py/blob/fcd8988d0b0fccf92e5b67f4ecf9ea1ce2e0387f/examples/alias_migration.py
"""
from datetime import datetime

from elasticsearch_dsl import IndexTemplate
from elasticsearch_dsl.connections import get_connection


def setup_index(doctype):
    """
    Create the index template in elasticsearch specifying the mappings and any
    settings to be used. This can be run at any time, ideally at every new code
    deploy.
    """

    alias = doctype._index._name
    pattern = '{alias}-*'.format(alias=alias)

    # create an index template
    index_template = doctype._index.as_template(alias, pattern)
    # upload the template into elasticsearch
    # potentially overriding the one already there
    index_template.save()

    # get the low level connection
    es = get_connection()
    # create the first index if it doesn't exist
    if not es.indices.exists_alias(alias):
        index = get_next_index(pattern)
        es.indices.create(index=index)
        es.indices.update_aliases(body={
            'actions': [
                {"add": {"alias": alias, "index": index}},
            ]
        })
    else:
        migrate(doctype, move_data=True, update_alias=True)


def get_next_index(pattern):
    return pattern.replace('*', datetime.now().strftime('%Y%m%d%H%M%S'))


def migrate(doctype, move_data=True, update_alias=True, delete_old_index=False):
    """
    Upgrade function that creates a new index for the data. Optionally it also can
    (and by default will) reindex previous copy of the data into the new index
    (specify ``move_data=False`` to skip this step) and update the alias to
    point to the latest index (set ``update_alias=False`` to skip).

    Note that while this function is running the application can still perform
    any and all searches without any loss of functionality. It should, however,
    not perform any writes at this time as those might be lost.
    """
    # get the low level connection
    es = get_connection()

    # get current index name from the alias
    current_index = list(es.indices.get_alias(doctype._index._name))[0]

    # construct a new index name by appending current timestamp
    alias = doctype._index._name
    pattern = '{alias}-*'.format(alias=alias)
    next_index = get_next_index(pattern)

    # create an index template
    index_template = IndexTemplate(alias, pattern)
    # add the DocType mappings
    index_template.doc_type(doctype)
    # upload the template into elasticsearch
    # potentially overriding the one already there
    index_template.save()

    # create new index, it will use the settings from the template
    es.indices.create(index=next_index)

    if move_data:
        # move data from current alias to the new index
        es.reindex(
            body={"source": {"index": alias}, "dest": {"index": next_index}},
            request_timeout=3600
        )
        # refresh the index to make the changes visible
        es.indices.refresh(index=next_index)

    if update_alias:
        # repoint the alias to point to the newly created index
        es.indices.update_aliases(body={
            'actions': [
                {"remove": {"alias": alias, "index": current_index}},
                {"add": {"alias": alias, "index": next_index}},
            ]
        })

    if delete_old_index:
        es.indices.delete(current_index)
