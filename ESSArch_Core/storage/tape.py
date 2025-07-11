import errno
import logging
import os
import re
import shlex
import tarfile
import time
from subprocess import PIPE, Popen

from django.conf import settings
from django.utils import timezone
from lxml import etree
from tenacity import retry, stop_after_attempt, wait_fixed

from ESSArch_Core.storage.exceptions import (
    MTFailedOperationException,
    MTInvalidOperationOrDeviceNameException,
    RobotException,
    RobotMountException,
    RobotMountTimeoutException,
    RobotUnmountException,
    TapeMountedError,
    TapeUnmountedError,
)
from ESSArch_Core.storage.tape_identification import (
    get_backend as get_tape_identification_backend,
)
from ESSArch_Core.util import (
    pretty_mb_per_sec,
    pretty_size,
    pretty_time_to_sec,
)

MB = 1024 * 1024
DEFAULT_TAPE_BLOCK_SIZE = 20 * 512


@retry(reraise=True, stop=stop_after_attempt(5), wait=wait_fixed(60))
def mount_tape(robot, slot, drive, media_id='?'):
    """
    Mounts tape from slot into drive

    Args:
        robot: The device used to mount the tape
        slot: Which slot to load from
        drive: Which drive to load to
        media_id: The id for the medium, e.g. barcode (only for logging)
    """

    logger = logging.getLogger('essarch.storage.tape')
    cmd = 'mtx -f %s load %d %d' % (robot, slot, drive)
    p = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE, universal_newlines=True)
    logger.debug(
        'Mounting tape {media_id} from {slot} to {drive} using {robot}: {cmd}'.format(
            media_id=media_id, slot=slot, drive=drive, robot=robot, cmd=cmd
        )
    )
    out, err = p.communicate()

    if p.returncode:
        if re.match(r'Drive \d+ Full \(Storage Element \d+ loaded\)', err):
            logger.warning(
                'Tried to mount already mounted tape {media_id} from {slot} to {drive} using {robot}'.format(
                    media_id=media_id, slot=slot, drive=drive, robot=robot
                )
            )
            raise TapeMountedError(err)

        logger.error(
            'Failed to mount tape {media_id} from {slot} to {drive} using {robot}, err: {err}, returncode: \
{rcode}'.format(media_id=media_id, slot=slot, drive=drive, robot=robot, err=err, rcode=p.returncode)
        )
        raise RobotMountException('%s, return code: %s' % (err, p.returncode))

    logger.info('Mounted tape {media_id} from {slot} to {drive} using {robot}'.format(
        media_id=media_id, slot=slot, drive=drive, robot=robot))
    return out


@retry(reraise=True, stop=stop_after_attempt(5), wait=wait_fixed(60))
def unmount_tape(robot, slot, drive, media_id='?'):
    """
    Unmounts tape from drive into slot

    Args:
        robot: The device used to unmount the tape
        slot: Which slot to unload to
        drive: Which drive to load from
        media_id: The id for the medium, e.g. barcode (only for logging)
    """

    logger = logging.getLogger('essarch.storage.tape')
    cmd = 'mtx -f %s unload %d %d' % (robot, slot, drive)
    p = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE, universal_newlines=True)
    logger.debug(
        'Unmounting tape {media_id} from {drive} to {slot} using {robot}: {cmd}'.format(
            media_id=media_id, drive=drive, slot=slot, robot=robot, cmd=cmd
        )
    )
    out, err = p.communicate()

    if p.returncode:
        if re.match(r'Data Transfer Element \d+ is Empty', err):
            logger.warning(
                'Tried to unmount already unmounted tape {media_id} from {drive} to {slot} using {robot}'.format(
                    media_id=media_id, drive=drive, slot=slot, robot=robot
                )
            )
            raise TapeUnmountedError(err)

        logger.error(
            'Failed to unmount tape {media_id} from {drive} to {slot} using {robot}, err: {err}, returncode: \
{rcode}'.format(media_id=media_id, drive=drive, slot=slot, robot=robot, err=err, rcode=p.returncode)
        )
        raise RobotUnmountException('%s, return code: %s' % (err, p.returncode))

    logger.info('Unmounted tape {media_id} from {drive} to {slot} using {robot}'.format(
        media_id=media_id, drive=drive, slot=slot, robot=robot))
    return out


def rewind_tape(drive):
    """
    Rewinds the tape in the given drive
    """

    logger = logging.getLogger('essarch.storage.tape')
    cmd = 'mt -f %s rewind' % (drive)
    p = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE, universal_newlines=True)
    logger.debug('Rewinding tape in {drive}: {cmd}'.format(drive=drive, cmd=cmd))
    out, err = p.communicate()

    if p.returncode:
        logger.error(
            'Failed to rewind tape in {drive}, err: {err}, returncode: {rcode}'.format(
                drive=drive, err=err, rcode=p.returncode
            )
        )

    if p.returncode == 1:
        raise MTInvalidOperationOrDeviceNameException(err)
    elif p.returncode == 2:
        raise MTFailedOperationException(err)

    logger.info('Rewinded tape in {drive}'.format(drive=drive))
    return out


def is_tape_drive_online(drive):
    """
    Checks if the given tape drive is online

    Args:
        drive: Which drive to check

    Returns:
        True if the drive is online, false otherwise
    """

    logger = logging.getLogger('essarch.storage.tape')
    cmd = 'mt -f %s status' % drive
    p = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE, universal_newlines=True)
    logger.debug('Checking if {drive} is online: {cmd}'.format(drive=drive, cmd=cmd))
    out, err = p.communicate()

    if p.returncode:
        logger.error(
            'Failed to check if {drive} is online, err: {err}, returncode: {rcode}'.format(
                drive=drive, err=err, rcode=p.returncode
            )
        )
        raise RobotException('%s, return code: %s' % (err, p.returncode))

    online = 'ONLINE' in out
    if online:
        logger.debug('{drive} is online, out: {out}'.format(drive=drive, out=out))
    else:
        logger.debug('{drive} is not online, out: {out}'.format(drive=drive, out=out))
    return online


def wait_to_come_online(drive, timeout=120):
    logger = logging.getLogger('essarch.storage.tape')
    logger.info('Waiting for {drive} to come online'.format(drive=drive))
    while timeout >= 0:
        if is_tape_drive_online(drive):
            return

        time.sleep(1)
        timeout -= 1

    logger.error('{drive} did not come online after {timeout} seconds'.format(drive=drive, timeout=120))
    raise RobotMountTimeoutException()


@retry(reraise=True, stop=stop_after_attempt(5), wait=wait_fixed(60))
def tape_empty(drive):
    logger = logging.getLogger('essarch.storage.tape')
    logger.info('Checking if tape in {drive} is empty'.format(drive=drive))
    try:
        rewind_tape(drive)
        logger.debug('Opening tape in {drive}'.format(drive=drive))
        tar = tarfile.open(drive, 'r|')
    except OSError:
        logger.warning('I/O error while opening tape in {drive}, retry'.format(drive=drive))
        rewind_tape(drive)
        try:
            logger.debug('Retry to open tape in {drive}'.format(drive=drive))
            tar = tarfile.open(drive, 'r|')
        except OSError as e:
            if e.errno == errno.EIO:
                logger.info('I/O error while opening tape in {drive}, it is empty'.format(drive=drive))
                rewind_tape(drive)
                return True
            logger.exception('Unknown error while opening tape in {drive}'.format(drive=drive))
            raise
    except tarfile.ReadError as e:
        if str(e) == 'empty file':
            logger.info('Empty file in tape in {drive}, tape is empty'.format(drive=drive))
            rewind_tape(drive)
            return True
        logger.exception('Unknown tarfile error while opening tape in {drive}'.format(drive=drive))
        raise
    else:
        logger.info('Tape in {drive} is not empty'.format(drive=drive))
        tar.close()
        rewind_tape(drive)
        return False


def create_tape_label(medium, xmlpath):
    root = etree.Element('label')

    label_tape = etree.SubElement(root, 'tape')
    label_tape.set('id', medium.medium_id)

    local_create_date = timezone.localtime(medium.create_date)
    label_tape.set('date', local_create_date.replace(microsecond=0).isoformat())

    label_format = etree.SubElement(root, 'format')
    label_format.set('format', str(medium.storage_target.default_format))
    label_format.set('blocksize', str(medium.storage_target.default_block_size))
    label_format.set('drivemanufacture', str(medium.storage_target.type))

    tree = etree.ElementTree(root)
    tree.write(xmlpath, pretty_print=True, xml_declaration=True, encoding='UTF-8')


def verify_tape_label(medium, xmlstring):
    logger = logging.getLogger('essarch.storage.tape')
    logger.info('Verifying tape label of {medium} against {xml}'.format(medium=medium, xml=xmlstring))
    try:
        root = etree.fromstring(xmlstring)
    except etree.XMLSyntaxError:
        logger.exception('{medium} tape label verification failed'.format(medium=medium))
        return False

    tape = root.find('tape')

    if tape is None:
        logger.error('{medium} tape label verification failed, tape element not found'.format(medium=medium))
        return False

    equal_id = tape.get('id') == str(medium.medium_id)

    if equal_id:
        logger.debug('{medium} tape label verification successful'.format(medium=medium))
    else:
        logger.error('{medium} tape label verification failed, tape element not found'.format(medium=medium))

    return equal_id


def read_tape(device, path='.', block_size=DEFAULT_TAPE_BLOCK_SIZE, medium_id=''):
    logger = logging.getLogger('essarch.storage.tape')
    logger.info(
        'Extracting content from {device} ({medium_id}) to {path}, with block size {size}'.format(
            device=device, medium_id=medium_id, path=path, size=block_size
        )
    )
    with tarfile.open(device, 'r|', bufsize=block_size) as tar:
        tar.extractall(path)


def write_to_tape(device, paths, block_size=DEFAULT_TAPE_BLOCK_SIZE, arcname=None, medium_id=''):
    """
    Writes content to a tape

    Args:
        device (str): The tape drive we are writing to, e.g. /dev/nst0
        paths: A string or iterator with the paths we are writing to the tape
        block_size (int, optional): The block size that will be used
        arcname (str, optional): If only one path is given then arcname can be used as the
            alternative name of the file on the tape.

    Raises:
        TypeError: If |`paths`| > 1 and `arcname` is not None
    """

    logger = logging.getLogger('essarch.storage.tape')
    if isinstance(paths, str):
        paths = [paths]

    logger.info(
        'Writing {paths} to {device} ({medium_id}) with block size {size}'.format(
            paths=",".join(paths), device=device, medium_id=medium_id, size=block_size
        )
    )

    if arcname is not None and len(paths) > 1:
        raise TypeError("'arcname' is not valid when write_to_tape is called with more than one path")

    with tarfile.open(device, 'w|', bufsize=block_size) as tar:
        tar.format = settings.TARFILE_FORMAT
        for path in paths:
            if len(paths) > 1 or arcname is None:
                arcname = os.path.basename(os.path.normpath(path))
            fsize = os.stat(path).st_size
            time_start = time.time()
            tar.add(path, arcname)
            time_end = time.time()

            time_elapsed = time_end - time_start
            fsize_mb = fsize / MB
            try:
                mb_per_sec = fsize_mb / time_elapsed
            except ZeroDivisionError:
                mb_per_sec = fsize_mb

            logger.info(
                'Added {} ({}) to {} ({}) at {} MB/Sec ({} sec)'.format(
                    path, pretty_size(fsize), device, medium_id, pretty_mb_per_sec(
                        mb_per_sec), pretty_time_to_sec(time_elapsed)
                )
            )


def get_tape_file_number(drive):
    logger = logging.getLogger('essarch.storage.tape')
    cmd = 'mt -f %s status' % drive
    p = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE, universal_newlines=True)
    logger.debug('Getting tape file number of {drive}: {cmd}'.format(drive=drive, cmd=cmd))
    out, err = p.communicate()

    if p.returncode:
        logger.error('Failed to get tape file number of {drive}'.format(drive=drive))

    if p.returncode == 1:
        raise MTInvalidOperationOrDeviceNameException(err)
    elif p.returncode == 2:
        raise MTFailedOperationException(err)

    file_line = ''
    for item in out.split("\n"):
        if "file number" in item.lower():
            file_line = item
            break
    file_number = int(file_line.split(',')[0].split('=')[1])
    logger.info('Got {num} as file number of {drive}'.format(num=file_number, drive=drive))
    return file_number


def set_tape_file_number(drive, num=0):
    logger = logging.getLogger('essarch.storage.tape')
    if num == 0:
        return rewind_tape(drive)

    current_num = get_tape_file_number(drive)

    new_num, op = get_tape_op_and_count(current_num, num)

    cmd = 'mt -f %s %s %d' % (drive, op, new_num)
    p = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE, universal_newlines=True)
    logger.debug('Setting file number of {drive} to {num}: {cmd}'.format(num=num, drive=drive, cmd=cmd))
    out, err = p.communicate()

    if p.returncode:
        logger.error('Failed to set tape file number of {drive} to {num}: {err}'.format(drive=drive, num=num, err=err))

    if p.returncode == 1:
        raise MTInvalidOperationOrDeviceNameException(err)
    elif p.returncode == 2:
        raise MTFailedOperationException(err)

    logger.info('File number of {drive} set to {num}'.format(num=num, drive=drive))
    return out


def get_tape_op_and_count(current_tape_file_num, new_file_num):
    if new_file_num < current_tape_file_num:
        op = 'bsfm'
        new_num = current_tape_file_num - new_file_num + 1
    else:
        new_num = new_file_num - current_tape_file_num

        if new_num > 0:
            op = 'fsf'
        elif new_num == 0:
            # We are already on the correct file, ensure we are at the beginning
            op = 'bsfm'
            new_num = 1
    return new_num, op


def robot_inventory(robot):
    """
    Updates the slots and drives in the robot

    Args:
        robot: Which robot to get the data from

    Returns:
        None
    """

    from ESSArch_Core.storage.models import (
        Robot,
        StorageMedium,
        TapeDrive,
        TapeSlot,
    )

    logger = logging.getLogger('essarch.storage.tape')
    backend_name = settings.ESSARCH_TAPE_IDENTIFICATION_BACKEND
    backend = get_tape_identification_backend(backend_name)

    cmd = 'mtx -f %s status' % robot
    p = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE, universal_newlines=True)
    logger.info('Inventoring {robot}: {cmd}'.format(robot=robot, cmd=cmd))
    out, err = p.communicate()

    if p.returncode:
        logger.error(
            'Failed to get inventory of {robot}, err: {err}, return code: {code}'.format(
                robot=robot, err=err, code=p.returncode
            )
        )
        raise RobotException('%s, return code: %s' % (err, p.returncode))

    robot = Robot.objects.get(device=robot)

    re_word = re.compile(r'\W+')
    for row in out.split('\n')[::-1]:  # Reverse to get (and create) slots first
        if re.match('Data Transfer Element', row):  # Find robot drives
            logger.debug('Found drive: {row}'.format(row=row))
            dt_el = re_word.split(row)

            drive_id = dt_el[3]
            status = dt_el[4]

            try:
                drive = TapeDrive.objects.get(drive_id=drive_id, robot=robot)
                logger.debug('Drive {row} (drive_id={drive}, robot={robot}) found in database'.format(
                    row=row, drive=drive_id, robot=robot
                )
                )
                if not drive.status == 20:
                    logger.info('Drive {row} (drive_id={drive}, robot={robot}) update status for drive \
from {drive_status} to 20'.format(row=row, drive=drive_id, robot=robot, drive_status=drive.status)
                                )
                    drive.status = 20
                    drive.save(update_fields=["status"])
                try:
                    if drive.storage_medium.tape_slot and not drive.storage_medium.tape_slot.status == 20:
                        drive.storage_medium.tape_slot.status = 20
                        drive.storage_medium.tape_slot.save(update_fields=["status"])
                except TapeDrive.storage_medium.RelatedObjectDoesNotExist:
                    pass

                if status == 'Full':
                    slot_id = dt_el[7]
                    medium_id = dt_el[10][:6]
                    backend.identify_tape(medium_id)
                    slot, created = TapeSlot.objects.update_or_create(
                        robot=robot, slot_id=slot_id, defaults={'medium_id': medium_id, 'status': 20}
                    )
                    num_updated = StorageMedium.objects.filter(medium_id=medium_id).update(
                        tape_slot=slot, tape_drive=drive, last_changed_local=timezone.now(),
                    )
                    if num_updated == 0:
                        logger.warning(
                            'No StorageMedium found with medium_id={medium} to update tape_slot={slot} and \
tape_drive={drive}'.format(medium=medium_id, slot=slot_id, drive=drive_id)
                        )
                        drive.status = 100
                        drive.save(update_fields=["status"])
                else:
                    StorageMedium.objects.filter(tape_drive=drive).update(
                        tape_drive=None, last_changed_local=timezone.now(),
                    )
            except TapeDrive.DoesNotExist:
                logger.warning(
                    'Drive {row} (drive_id={drive}, robot={robot}) not found in database'.format(
                        row=row, drive=drive_id, robot=robot
                    )
                )

        if re.match(r'\ *Storage Element', row):  # Find robot slots
            if not re.search('EXPORT', row):
                logger.debug('Found slot: {row}'.format(row=row))
                s_el = re_word.split(row)

                slot_id = s_el[3]
                status = s_el[4]

                if status == 'Full':
                    try:
                        medium_id = s_el[6][:6]
                    except IndexError:
                        logger.warning('Missing medium id for tape slot: {slot}'.format(slot=slot_id))
                        medium_id = None
                    backend.identify_tape(medium_id)

                    slot, created = TapeSlot.objects.update_or_create(
                        robot=robot, slot_id=slot_id, defaults={'medium_id': medium_id, 'status': 20}
                    )
                    if created:
                        logger.info(
                            'Created tape slot with slot_id={slot}, medium_id={medium}'.format(
                                slot=slot_id, medium=medium_id
                            )
                        )
                    else:
                        logger.info(
                            'Updated tape slot with slot_id={slot}, medium_id={medium}'.format(
                                slot=slot_id, medium=medium_id
                            )
                        )

                    StorageMedium.objects.filter(tape_slot=slot).exclude(medium_id=medium_id).update(
                        tape_slot=None, tape_drive=None, last_changed_local=timezone.now(),
                    )
                    StorageMedium.objects.filter(medium_id=medium_id).update(
                        tape_slot=slot, tape_drive=None, last_changed_local=timezone.now(),
                    )
                else:
                    slot, created = TapeSlot.objects.get_or_create(robot=robot, slot_id=slot_id)
                    if created:
                        logger.info('Created tape slot with slot_id={slot}'.format(slot=slot_id))
                    elif status == 'Empty' and slot.medium_id is not None:
                        slot.medium_id = None
                        slot.save(update_fields=['medium_id'])
                        StorageMedium.objects.filter(tape_slot=slot).update(
                            tape_slot=None, tape_drive=None, last_changed_local=timezone.now(),
                        )
                    elif slot.status == 100:
                        slot.status = 20
                        slot.save(update_fields=['status'])
