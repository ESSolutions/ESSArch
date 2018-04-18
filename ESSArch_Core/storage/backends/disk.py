import logging
import os
import tarfile
from contextlib import contextmanager

from ESSArch_Core.storage.backends.base import BaseStorageBackend
from ESSArch_Core.storage.copy import copy
from ESSArch_Core.storage.models import DISK, StorageObject

logger = logging.getLogger('essarch.storage.backends.disk')


class DiskStorageBackend(BaseStorageBackend):
    type = DISK

    def _extract(self, storage_object, dst):
        path = storage_object.get_full_path()

        with tarfile.open(path) as t:
            root = os.path.commonprefix(t.getnames())
            t.extractall(dst)

        return os.path.join(dst, root)

    @contextmanager
    def open(self, storage_object, file, *args, **kwargs):
        path = os.path.join(storage_object.content_location_value, file)
        f = open(path, *args, **kwargs)
        yield f
        f.close()

    def read(self, storage_object, dst, extract=False, include_xml=True, block_size=65536):
        medium = storage_object.storage_medium
        target = medium.storage_target
        ip = storage_object.ip
        src = storage_object.get_full_path()

        if storage_object.container:
            src_tar = src + '.tar'
            src_xml = src + '.xml'
            src_aic_xml = os.path.join(target.target, str(ip.aic.pk)) + '.xml'

            if include_xml:
                copy(src_xml, dst, block_size=block_size)
                copy(src_aic_xml, dst, block_size=block_size)
            if extract:
                return self._extract(storage_object, dst)
            else:
                return copy(src_tar, dst, block_size=block_size)
        else:
            return copy(src, dst, block_size=block_size)

    def write(self, src, ip, storage_method, storage_medium, create_obj=True, update_obj=None, block_size=65536):
        if update_obj is not None and create_obj:
            raise ValueError("Cannot both update and create storage object")

        logger.debug('writing {src} to {medium}'.format(src=src, medium=storage_medium))

        storage_target = storage_medium.storage_target
        dst = storage_target.target
        if not storage_method.containers:
            dst = os.path.join(dst, ip.object_identifier_value)
        else:
            dst = os.path.join(dst, os.path.basename(src))

        copy(src, dst, block_size=block_size)

        if create_obj:
            return StorageObject.objects.create(
                content_location_value=dst,
                content_location_type=DISK,
                ip=ip, storage_medium=storage_medium,
                container=storage_method.containers,
            )
        elif update_obj:
            return update_obj

