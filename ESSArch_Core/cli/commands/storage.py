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
    global StorageMedium, StorageObject
    from ESSArch_Core.storage.models import StorageMedium, StorageObject


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


@click.command()
@click.option("--id", type=str, help="Select storage medium for ID (PK) to update.")
@click.option("--medium_id", type=str, help="Select storage medium for medium_id to update.")
@click.option("--location", type=str, help="Update location for storage medium.")
@click.option("--location_status", type=str, help="Update location_status for storage medium.")
@click.option("--status", type=str, help="Update status for storage medium(0=Inactive, 20=Write, 30=Full, 100=FAIL).")
@click.option("--preview", is_flag=True, help="Preview the storage medium that would be updated.")
def update_storageMedium(id=None, medium_id=None, location=None, location_status=None, status=None, preview=False):
    """Update storageMedium."""
    import_globally()
    if id is not None:
        storageMedium_obj = StorageMedium.objects.get(id=id)
    elif medium_id is not None:
        storageMedium_obj = StorageMedium.objects.get(medium_id=medium_id)

    if location is not None:
        storageMedium_obj.location = location
    if location_status is not None:
        storageMedium_obj.location_status = location_status
    if status is not None:
        storageMedium_obj.status = int(status)
    if preview:
        print(f"Preview: Storage medium {storageMedium_obj.medium_id} would be updated.")
        return
    storageMedium_obj.save()
    print(f"Storage medium {storageMedium_obj.medium_id} has been updated.")
