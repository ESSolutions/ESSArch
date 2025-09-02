"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2024 ES Solutions AB

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

import click

from ESSArch_Core.config.decorators import initialize


@initialize
def import_globally():
    global StorageObject
    from ESSArch_Core.storage.models import StorageObject


@click.command()
@click.option("--id", type=str, help="Remove storage object ID.")
@click.option("--ip_id", type=str, help="Remove all storage objects for ip_id (object_identifier_value).")
@click.option("--medium_id", type=str, help="Remove all storage objects for medium_id.")
@click.option("--preview", is_flag=True, help="Preview the storage that would be removed.")
def remove_storage(id=None, ip_id=None, medium_id=None, preview=False):
    """Remove storage objects."""
    import_globally()
    storage_to_remove = []
    if id is not None:
        storage_objs = StorageObject.objects.filter(id=id)
        if storage_objs.exists():
            storage_to_remove.append(storage_objs.get())
    if ip_id is not None:
        for storage_obj in StorageObject.objects.filter(ip__object_identifier_value=ip_id):
            storage_to_remove.append(storage_obj)
    if medium_id is not None:
        for storage_obj in StorageObject.objects.filter(storage_medium__medium_id=medium_id):
            storage_to_remove.append(storage_obj)

    if not storage_to_remove:
        print("No storage objects found to remove.")
        exit(1)

    for storage_obj in storage_to_remove:
        if preview:
            print(f"Preview: Storage object {storage_obj.id} for information package {storage_obj} would be removed.")
            continue
        storage_obj.delete()
        print(f"Storage object {storage_obj.id} for information package {storage_obj} has been removed.")
