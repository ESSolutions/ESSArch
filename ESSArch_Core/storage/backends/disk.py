import errno
import logging
import os
import shutil
import tarfile

from ESSArch_Core.storage.backends.base import BaseStorageBackend
from ESSArch_Core.storage.copy import copy, DEFAULT_BLOCK_SIZE
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

    def open(self, storage_object, file, *args, **kwargs):
        path = os.path.join(storage_object.content_location_value, file)
        return open(path, *args, **kwargs)

    def read(self, storage_object, dst, extract=False, include_xml=True, block_size=DEFAULT_BLOCK_SIZE):
        src = storage_object.get_full_path()

        if storage_object.container:
            ip = storage_object.ip
            target = storage_object.storage_medium.storage_target.target
            src_tar = src
            src_xml = os.path.splitext(src)[0] + '.xml'
            src_aic_xml = os.path.join(target, str(ip.aic.pk)) + '.xml'

            if include_xml:
                copy(src_xml, dst, block_size=block_size)
                copy(src_aic_xml, dst, block_size=block_size)
            if extract:
                return self._extract(storage_object, dst)
            else:
                return copy(src_tar, dst, block_size=block_size)
        else:
            return copy(src, dst, block_size=block_size)

    def write(self, src, ip, storage_method, storage_medium, block_size=DEFAULT_BLOCK_SIZE):
        if isinstance(src, str):
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

    def delete(self, storage_object):
        path = storage_object.content_location_value
        if not storage_object.container:
            try:
                shutil.rmtree(path)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise
        else:
            tar = path
            xml = os.path.splitext(tar)[0] + '.xml'
            aic_xml = os.path.join(os.path.dirname(tar), str(storage_object.ip.aic.pk) + '.xml')
            files = [tar, xml, aic_xml]
            for f in files:
                try:
                    os.remove(f)
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise
