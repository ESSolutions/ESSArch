import errno
import logging
import os
import pickle
import shutil
import tarfile
import tempfile
import time

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import IntegerField
from django.db.models.functions import Cast
from django.utils import timezone

from ESSArch_Core.storage.backends.base import BaseStorageBackend
from ESSArch_Core.storage.copy import copy
from ESSArch_Core.storage.exceptions import StorageMediumFull
from ESSArch_Core.storage.models import (
    TAPE,
    RobotQueue,
    StorageObject,
    TapeDrive,
)
from ESSArch_Core.storage.tape import (
    DEFAULT_TAPE_BLOCK_SIZE,
    read_tape,
    set_tape_file_number,
    write_to_tape,
)

User = get_user_model()
logger = logging.getLogger('essarch.storage.backends.tape')


class TapeStorageBackend(BaseStorageBackend):
    type = TAPE

    @staticmethod
    def lock_or_wait_for_drive(storage_medium, io_lock_key, wait_timeout=10 * 60):
        drive = storage_medium.tape_drive
        if isinstance(io_lock_key, StorageObject):
            io_lock_key = pickle.dumps(str(io_lock_key.pk))
        else:
            io_lock_key = pickle.dumps(io_lock_key)

        if not drive.is_locked():
            if cache.add(drive.get_lock_key(), io_lock_key):
                drive.last_change = timezone.now()
                drive.save(update_fields=['last_change'])
                logger.debug('Storage medium {} ({}) is now locked for request {}'.format(
                    storage_medium.medium_id, str(storage_medium.pk), pickle.loads(io_lock_key)))
            else:
                raise ValueError('Failed to set drivelock for Storage medium {} ({}) with request {}'.format(
                    storage_medium.medium_id, str(storage_medium.pk), pickle.loads(io_lock_key)))
        else:
            timeout_at = time.monotonic() + wait_timeout
            while drive.is_locked():
                drive_lock_key = pickle.loads(cache.get(drive.get_lock_key()))
                logger.debug('Storage medium {} ({}) is already locked with {} and not requested {}'.format(
                    storage_medium.medium_id, str(storage_medium.pk),
                    drive_lock_key, pickle.loads(io_lock_key)))
                if time.monotonic() > timeout_at:
                    raise ValueError("Timeout waiting for drivelock for storage medium {} ({}) with \
request {}".format(storage_medium.medium_id, str(storage_medium.pk), pickle.loads(io_lock_key)))
                time.sleep(1)

            if cache.add(drive.get_lock_key(), io_lock_key):
                drive.last_change = timezone.now()
                drive.save(update_fields=['last_change'])
                logger.debug('Storage medium {} ({}) is now locked for request {}'.format(
                    storage_medium.medium_id, str(storage_medium.pk), pickle.loads(io_lock_key)))
            else:
                raise ValueError('Failed to set drivelock for Storage medium {} ({}) with request {}'.format(
                    storage_medium.medium_id, str(storage_medium.pk), pickle.loads(io_lock_key)))

    @staticmethod
    def wait_for_media_transit(storage_medium, wait_timeout=10 * 60):
        timeout_at = time.monotonic() + wait_timeout
        while storage_medium.tape_drive.locked:
            logger.debug('Storage medium {} ({}) is in transit, sleeps for 5 seconds and checking again'.format(
                storage_medium.medium_id, str(storage_medium.pk)))
            if time.monotonic() > timeout_at:
                raise ValueError("Timeout waiting for transit of storage medium {} ({})".format(
                    storage_medium.medium_id, str(storage_medium.pk)))
            time.sleep(5)
            storage_medium.refresh_from_db()

    def prepare_for_io(self, storage_medium, io_lock_key=None, wait_timeout=10 * 60):
        if storage_medium.tape_drive is not None:
            self.wait_for_media_transit(storage_medium)

        storage_medium.refresh_from_db()
        if storage_medium.tape_drive is not None:
            # already mounted
            if io_lock_key is not None:
                logger.debug('Storage medium {} ({}) is already mounted'.format(
                    storage_medium.medium_id, str(storage_medium.pk)))
                self.lock_or_wait_for_drive(storage_medium, io_lock_key)
            else:
                logger.debug('Storage medium {} ({}) is already mounted without lock key'.format(
                    storage_medium.medium_id, str(storage_medium.pk)))
            return

        logger.debug('Queueing mount of storage medium {} ({})'.format(
            storage_medium.medium_id, str(storage_medium.pk)))
        rq, _ = RobotQueue.objects.get_or_create(
            user=User.objects.get(username='system'),
            storage_medium=storage_medium,
            robot=storage_medium.tape_slot.robot,
            req_type=10, status__in=[0, 2], defaults={'status': 0},
        )

        while RobotQueue.objects.filter(id=rq.id).exists():
            logger.debug('Wait for the mount request to complete for storage medium {} ({})'.format(
                storage_medium.medium_id, str(storage_medium.pk)))
            time.sleep(5)

        storage_medium.refresh_from_db()
        if storage_medium.tape_drive is not None:
            self.wait_for_media_transit(storage_medium)

        storage_medium.refresh_from_db()
        if storage_medium.tape_drive is not None:
            if io_lock_key is not None:
                logger.debug('Storage medium {} ({}) is now mounted'.format(
                    storage_medium.medium_id, str(storage_medium.pk)))
                self.lock_or_wait_for_drive(storage_medium, io_lock_key)
            else:
                logger.debug('Storage medium {} ({}) is now mounted without lock key'.format(
                    storage_medium.medium_id, str(storage_medium.pk)))
            return
        else:
            raise ValueError("Tape not mounted")

    def prepare_for_read(self, storage_medium, io_lock_key=None):
        """Prepare tape for reading by mounting it"""

        return self.prepare_for_io(storage_medium, io_lock_key)

    def read(self, storage_object, dst, extract=False, include_xml=True, block_size=DEFAULT_TAPE_BLOCK_SIZE):
        tape_pos = int(storage_object.content_location_value)
        medium = storage_object.storage_medium
        ip = storage_object.ip
        block_size = medium.block_size * 512

        # TODO: Create temp dir inside configured temp directory
        tmp_path = tempfile.mkdtemp()

        try:
            drive = TapeDrive.objects.get(storage_medium=medium)
        except TapeDrive.DoesNotExist:
            raise ValueError("Tape not mounted")

        set_tape_file_number(drive.device, tape_pos)
        read_tape(drive.device, path=tmp_path, block_size=block_size)

        drive.last_change = timezone.now()
        drive.save(update_fields=['last_change'])
        logger.debug('Release lock for drive {} and storage medium {} ({})'.format(
            drive.pk, medium.medium_id, str(medium.pk)))
        cache.delete_pattern(drive.get_lock_key())

        src = os.path.join(tmp_path, ip.object_identifier_value)
        aic_xml = True if ip.aic else False
        if storage_object.container:
            src_tar = src + '.tar'
            src_xml = os.path.join(tmp_path, ip.package_mets_path.split('/')[-1])
            if aic_xml:
                src_aic_xml = os.path.join(tmp_path, str(ip.aic.pk)) + '.xml'

            if include_xml:
                copy(src_xml, dst, block_size=block_size)
                if aic_xml:
                    try:
                        copy(src_aic_xml, dst, block_size=block_size)
                    except FileNotFoundError as e:
                        logger.warning('AIC xml file does not exists for IP: {}. Error: {}'.format(ip, e))
            if extract:
                with tarfile.open(src_tar) as t:
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
                    new = os.path.join(dst, root)
            else:
                new = copy(src_tar, dst, block_size=block_size)
        else:
            new = copy(src, dst, block_size=block_size)

        try:
            shutil.rmtree(tmp_path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
        return new

    def prepare_for_write(self, storage_medium, io_lock_key=None):
        """Prepare tape for writing by mounting it"""

        return self.prepare_for_io(storage_medium, io_lock_key)

    def write(self, src, ip, container, storage_medium, block_size=DEFAULT_TAPE_BLOCK_SIZE):
        block_size = storage_medium.block_size * 512

        last_written_obj = StorageObject.objects.filter(
            storage_medium=storage_medium
        ).annotate(
            content_location_value_int=Cast('content_location_value', IntegerField())
        ).order_by('content_location_value_int').only('content_location_value').last()

        if last_written_obj is None:
            tape_pos = 1
        else:
            tape_pos = last_written_obj.content_location_value_int + 1

        try:
            drive = TapeDrive.objects.get(storage_medium=storage_medium)
        except TapeDrive.DoesNotExist:
            raise ValueError("Tape not mounted")

        try:
            set_tape_file_number(drive.device, tape_pos)
            write_to_tape(drive.device, src, block_size=block_size)
        except OSError as e:
            if e.errno == errno.ENOSPC:
                storage_medium.mark_as_full()
                raise StorageMediumFull('No space left on storage medium "{}"'.format(str(storage_medium.pk)))
            else:
                logger.exception('Error occurred when writing to tape')
                raise

        drive.last_change = timezone.now()
        drive.save(update_fields=['last_change'])
        cache.delete_pattern(drive.get_lock_key())

        return StorageObject.objects.create(
            content_location_value=tape_pos,
            content_location_type=TAPE,
            ip=ip, storage_medium=storage_medium,
            container=container
        )

    def delete(self, storage_object):
        pass

    @classmethod
    def post_mark_as_full(cls, storage_medium):
        """Called after a medium has been successfully marked as full"""

        drive = str(storage_medium.drive)

        logger.debug('Release lock for drive {} and storage medium {} ({})'.format(
            drive.pk, storage_medium.medium_id, str(storage_medium.pk)))
        cache.delete_pattern(drive.get_lock_key())

        logger.debug('Queueing unmount of storage medium {} ({})'.format(
            storage_medium.medium_id, str(storage_medium.pk)))
        rq, _ = RobotQueue.objects.get_or_create(
            user=User.objects.get(username='system'),
            storage_medium=storage_medium,
            robot=storage_medium.tape_slot.robot,
            req_type=20, status__in=[0, 2], defaults={'status': 0},
        )

        while RobotQueue.objects.filter(id=rq.id).exists():
            logger.debug('Wait for the unmount request to complete for storage medium {} ({})'.format(
                storage_medium.medium_id, str(storage_medium.pk)))
            time.sleep(1)
