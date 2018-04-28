import logging
import os
import tarfile
from contextlib import contextmanager

import six

from ESSArch_Core.storage.backends.base import BaseStorageBackend
from ESSArch_Core.storage.copy import copy
from ESSArch_Core.storage.models import DISK, StorageObject

logger = logging.getLogger('essarch.storage.backends.disk')


class DiskStorageBackend(BaseStorageBackend):
    type = DISK

    def _extract(self, storage_object, dst):
        path = storage_object.get_full_path()
        logger.debug('Extracting {src} to {dst}'.format(src=path, dst=dst))

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

    def write(self, src, ip, storage_method, storage_medium, block_size=65536):
        if isinstance(src, six.string_types):
            src = [src]
        dst = storage_medium.storage_target.target
        logger.debug('Writing {src} to {dst}'.format(src=', '.join(src), dst=dst))

        if not os.path.isdir(dst):
            msg = "{dst} is not a directory".format(dst=dst)
            logger.error(msg)
            raise ValueError(msg)

        if not storage_method.containers:
            dst = os.path.join(dst, ip.object_identifier_value)

        for idx, f in enumerate(src):
            new = copy(f, dst, block_size=block_size)
            if idx == 0:
                content_location_value = new

        return StorageObject.objects.create(
            content_location_value=content_location_value,
            content_location_type=DISK,
            ip=ip, storage_medium=storage_medium,
            container=storage_method.containers,
        )

