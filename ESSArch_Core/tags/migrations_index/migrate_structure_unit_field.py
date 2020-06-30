"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2020 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""
import django

django.setup()

from pydoc import locate  # noqa isort:skip

from django.conf import settings  # noqa isort:skip
from elasticsearch.client import IngestClient  # noqa isort:skip
from elasticsearch_dsl.connections import get_connection  # noqa isort:skip

from ESSArch_Core.search import alias_migration  # noqa isort:skip


def get_indexes(indexes):
    all_indexes = getattr(settings, 'ELASTICSEARCH_INDEXES', {'default': {}})['default']

    if indexes:
        indexes = {key: all_indexes[key] for key in indexes}
    else:
        indexes = all_indexes

    return [locate(cls) for name, cls in indexes.items()]


def putPipelines():
    conn = get_connection()
    client = IngestClient(conn)
    client.put_pipeline(id='rename_structure_unit_description', body={
        'description': "Rename field _source.description to _source.desc",
        'processors': [
            {
                "rename": {
                    "field": "_source.description",
                    "target_field": "_source.desc",
                },
            },
        ]
    })


def deletePipelines():
    conn = get_connection()
    client = IngestClient(conn)
    client.delete_pipeline(id='rename_structure_unit_description')


def migrate_structure_unit():
    index = get_indexes(['structure_unit'])[0]
    alias_migration.migrate(index, move_data=True, update_alias=True, delete_old_index=False,
                            reindex_pipeline='rename_structure_unit_description')
    print('done')


if __name__ == '__main__':
    putPipelines()
    migrate_structure_unit()
    deletePipelines
