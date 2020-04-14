import os

from ESSArch_Core.storage.models import (
    StorageMedium,
    StorageMethod,
    StorageMethodTargetRelation,
    StorageObject,
    StorageTarget,
)


def add_storage_method_rel(storage_type, target_name, status):
    storage_method = StorageMethod.objects.create(
        type=storage_type,
    )
    storage_target = StorageTarget.objects.create(
        name=target_name,
    )

    return StorageMethodTargetRelation.objects.create(
        storage_method=storage_method,
        storage_target=storage_target,
        status=status,
    )


def add_storage_medium(target, status, medium_id=''):
    return StorageMedium.objects.create(
        storage_target=target, medium_id=medium_id,
        status=status, location_status=50, block_size=1024, format=103,
    )


def add_storage_obj(ip, medium, loc_type, loc_value, create_dir=False):
    obj = StorageObject.objects.create(
        ip=ip, storage_medium=medium,
        content_location_type=loc_type,
        content_location_value=loc_value,
    )

    if create_dir:
        os.makedirs(obj.get_full_path(), exist_ok=True)

    return obj
