import errno
import logging
import os
import shutil
import tarfile
import tempfile

from celery.result import allow_join_result
from django.db.models import IntegerField
from django.db.models.functions import Cast
from django.utils import timezone

from ESSArch_Core.storage.backends.base import BaseStorageBackend
from ESSArch_Core.storage.copy import copy
from ESSArch_Core.storage.exceptions import StorageMediumFull
from ESSArch_Core.storage.models import TAPE, StorageObject, TapeDrive
from ESSArch_Core.storage.tape import (
    DEFAULT_TAPE_BLOCK_SIZE,
    read_tape,
    set_tape_file_number,
    write_to_tape,
)
from ESSArch_Core.WorkflowEngine.models import ProcessTask

logger = logging.getLogger('essarch.storage.backends.tape')


class TapeStorageBackend(BaseStorageBackend):
    type = TAPE

    @staticmethod
    def prepare_for_io(storage_medium):
        if storage_medium.tape_drive is not None:
            # already mounted
            return

        with allow_join_result():
            logger.debug('Queueing mount of storage medium "{}"'.format(str(storage_medium.pk)))
            mount_task = ProcessTask.objects.create(
                name="ESSArch_Core.tasks.MountTape",
                args=[str(storage_medium.pk)],
                eager=False,
            )
            mount_task.run().get()

    def prepare_for_read(self, storage_medium):
        """Prepare tape for reading by mounting it"""

        return self.prepare_for_io(storage_medium)

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

        src = os.path.join(tmp_path, ip.object_identifier_value)
        if storage_object.container:
            src_tar = src + '.tar'
            src_xml = src + '.xml'
            src_aic_xml = os.path.join(tmp_path, str(ip.aic.pk)) + '.xml'

            if include_xml:
                copy(src_xml, dst, block_size=block_size)
                copy(src_aic_xml, dst, block_size=block_size)
            if extract:
                with tarfile.open(src_tar) as t:
                    root = os.path.commonprefix(t.getnames())
                    t.extractall(dst)
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

    def prepare_for_write(self, storage_medium):
        """Prepare tape for writing by mounting it"""

        return self.prepare_for_io(storage_medium)

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

        drive_id = str(storage_medium.drive.pk)

        with allow_join_result():
            # unmount this tape
            logger.debug('Queueing unmount of tape in drive {}'.format(drive_id))
            unmount_task = ProcessTask.objects.create(
                name="ESSArch_Core.tasks.UnmountTape",
                args=[str(drive_id)],
                eager=False,
            )
            unmount_task.run().get()
