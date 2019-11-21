import errno
import io
import logging
import os
from os import walk

import boto3
from django.conf import settings

from ESSArch_Core.storage.backends.base import BaseStorageBackend
from ESSArch_Core.storage.copy import DEFAULT_BLOCK_SIZE
from ESSArch_Core.storage.models import CAS, StorageObject

logger = logging.getLogger('essarch.storage.backends.s3')
AWS = settings.AWS

s3 = boto3.resource('s3',
                    aws_access_key_id=AWS.get('ACCESS_KEY_ID'),
                    aws_secret_access_key=AWS.get('SECRET_ACCESS_KEY'),
                    endpoint_url=AWS.get('ENDPOINT_URL'))


class S3StorageBackend(BaseStorageBackend):
    type = CAS

    def _extract(self, storage_object, dst):
        raise NotImplementedError

    def open(self, storage_object, file, *args, **kwargs):
        data = io.StringIO()
        bucket_name, key = storage_object.content_location_value.split('/', 1)
        key = os.path.join(key, file)
        bucket = s3.Bucket(bucket_name)
        bucket.download_fileobj(key, data)
        data.seek(0)
        return data

    def read(self, storage_object, dst, extract=False, include_xml=True, block_size=DEFAULT_BLOCK_SIZE):
        ip = storage_object.ip

        bucket_name, key = storage_object.content_location_value.split('/', 1)
        bucket = s3.Bucket(bucket_name)

        if storage_object.container:
            src_tar = key
            src_xml = os.path.splitext(key)[0] + '.xml'
            src_aic_xml = str(ip.aic.pk) + '.xml'
            dst_tar = os.path.join(dst, os.path.basename(src_tar))
            dst_xml = os.path.join(dst, os.path.basename(src_xml))
            dst_aic_xml = os.path.join(dst, os.path.basename(src_aic_xml))

            if include_xml:
                bucket.download_file(src_xml, dst_xml)
                bucket.download_file(src_aic_xml, dst_aic_xml)
            if extract:
                return self._extract(storage_object, dst)
            else:
                bucket.download_file(src_tar, dst_tar)
                return dst_tar
        else:
            for object_summary in bucket.objects.filter(Prefix=key):
                dst_file = os.path.join(dst, os.path.basename(object_summary.key))
                bucket.download_file(object_summary.key, dst_file)
            return dst

    def write(self, src, ip, container, storage_medium, block_size=DEFAULT_BLOCK_SIZE):
        if isinstance(src, str):
            src = [src]
        dst = storage_medium.storage_target.target
        logger.debug('Writing {src} to {dst}'.format(src=', '.join(src), dst=dst))

        bucket_name = dst
        bucket = s3.Bucket(bucket_name)

        content_location_value = None
        for f in src:
            try:
                key = os.path.basename(f)
                bucket.upload_file(f, key)
                if content_location_value is None:
                    content_location_value = '{}/{}'.format(bucket_name, key)
            except IOError as e:
                if e.errno != errno.EISDIR:
                    raise

                parent_dir = os.path.dirname(f)
                for root, _dirs, files in walk(f):
                    for fi in files:
                        srcf = os.path.join(root, fi)
                        dstf = os.path.relpath(os.path.join(root, fi), parent_dir)
                        bucket.upload_file(srcf, dstf)

                if content_location_value is None:
                    content_location_value = '{}/{}'.format(bucket_name, os.path.basename(f))

        return StorageObject.objects.create(
            content_location_value=content_location_value,
            content_location_type=CAS,
            ip=ip, storage_medium=storage_medium,
            container=container,
        )

    def delete(self, storage_object):
        bucket_name, key = storage_object.content_location_value.split('/', 1)
        bucket = s3.Bucket(bucket_name)
        bucket.objects.filter(Prefix=key).delete()
