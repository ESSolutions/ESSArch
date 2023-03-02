import errno
import logging
import os
import shutil
import tarfile
from os import walk

from glob2 import iglob

from ESSArch_Core.storage.backends.base import BaseStorageBackend
from ESSArch_Core.storage.copy import DEFAULT_BLOCK_SIZE, copy
from ESSArch_Core.storage.models import DISK, StorageObject
from ESSArch_Core.util import normalize_path, open_file

logger = logging.getLogger('essarch.storage.backends.disk')


class DiskStorageBackend(BaseStorageBackend):
    type = DISK

    def _extract(self, storage_object, dst):
        path = storage_object.get_full_path()
        logger.debug('Extracting {src} to {dst}'.format(src=path, dst=dst))

        with tarfile.open(path) as t:
            root = os.path.commonprefix(t.getnames())

            def is_within_directory(directory, target):
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
                prefix = os.path.commonprefix([abs_directory, abs_target])

                return prefix == abs_directory

            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")

                tar.extractall(path, members, numeric_owner=numeric_owner)

            safe_extract(t, dst)
        return os.path.join(dst, root)

    def open(self, storage_object: StorageObject, file, mode='r', *args, **kwargs):
        if storage_object.container:
            return open_file(
                file, *args, container=storage_object.get_full_path(),
                container_prefix=storage_object.ip.object_identifier_value, **kwargs
            )

        path = os.path.join(storage_object.get_full_path(), file)
        return open(path, mode, *args, **kwargs)

    def read(self, storage_object, dst, extract=False, include_xml=True, block_size=DEFAULT_BLOCK_SIZE):
        src = storage_object.get_full_path()

        if storage_object.container:
            ip = storage_object.ip
            aic_xml = True if ip.aic else False
            target = storage_object.storage_medium.storage_target.target
            src_tar = src
            src_xml = os.path.join(target, ip.package_mets_path.split('/')[-1])
            if aic_xml:
                src_aic_xml = os.path.join(target, str(ip.aic.pk)) + '.xml'

            if include_xml:
                copy(src_xml, dst, block_size=block_size)
                if aic_xml:
                    try:
                        copy(src_aic_xml, dst, block_size=block_size)
                    except FileNotFoundError as e:
                        logger.warning('AIC xml file does not exists for IP: {}. Error: {}'.format(ip, e))
            if extract:
                return self._extract(storage_object, dst)
            else:
                return copy(src_tar, dst, block_size=block_size)
        else:
            return copy(src, dst, block_size=block_size)

    def write(self, src, ip, container, storage_medium, block_size=DEFAULT_BLOCK_SIZE):
        if isinstance(src, str):
            src = [src]
        dst = storage_medium.storage_target.target
        logger.debug('Writing {src} to {dst}'.format(src=', '.join(src), dst=dst))

        if not os.path.isdir(dst):
            msg = "{dst} is not a directory".format(dst=dst)
            logger.error(msg)
            raise ValueError(msg)

        if not container:
            dst = os.path.join(dst, ip.object_identifier_value)

        for idx, f in enumerate(src):
            new = copy(f, dst, block_size=block_size)
            if idx == 0:
                content_location_value = new

        _, content_location_value = os.path.split(content_location_value)

        return StorageObject.objects.create(
            content_location_value=content_location_value,
            content_location_type=DISK,
            ip=ip, storage_medium=storage_medium,
            container=container,
        )

    def list_files(self, storage_object, pattern, case_sensitive=True):
        if storage_object.container:
            raise NotImplementedError

        datadir = storage_object.get_full_path()

        if pattern is None:
            for root, _dirs, files in walk(datadir):
                rel = os.path.relpath(root, datadir)
                for f in files:
                    yield normalize_path(os.path.join(rel, f))
        else:
            for path in iglob(datadir + '/' + pattern, case_sensitive=case_sensitive):
                if os.path.isdir(path):
                    for root, _dirs, files in walk(path):
                        rel = os.path.relpath(root, datadir)

                        for f in files:
                            yield normalize_path(os.path.join(rel, f))

                else:
                    yield normalize_path(os.path.relpath(path, datadir))

    def delete(self, storage_object):
        path = storage_object.get_full_path()
        if not storage_object.container:
            try:
                shutil.rmtree(path)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise
        else:
            tar = path
            xml = os.path.splitext(tar)[0] + '.xml'
            aic_xml = True if storage_object.ip.aic else False
            if aic_xml:
                aic_xml = os.path.join(os.path.dirname(tar), str(storage_object.ip.aic.pk) + '.xml')
                files = [tar, xml, aic_xml]
            else:
                files = [tar, xml]
            for f in files:
                try:
                    os.remove(f)
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise
