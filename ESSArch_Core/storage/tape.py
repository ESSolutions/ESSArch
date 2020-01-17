import errno
import logging
import os
import re
import tarfile
import time
from subprocess import PIPE, Popen

from django.conf import settings
from django.utils.timezone import localtime
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

DEFAULT_TAPE_BLOCK_SIZE = 20 * 512
logger = logging.getLogger('essarch.storage.tape')


@retry(reraise=True, stop=stop_after_attempt(5), wait=wait_fixed(60))
def mount_tape(robot, slot, drive):
    """
    Mounts tape from slot into drive

    Args:
        robot: The device used to mount the tape
        slot: Which slot to load from
        drive: Which drive to load to
    """

    cmd = 'mtx -f %s load %d %d' % (robot, slot, drive)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    logger.debug(
        'Mounting tape from {slot} to {drive} using {robot}: {cmd}'.format(
            slot=slot, drive=drive, robot=robot, cmd=cmd
        )
    )
    out, err = p.communicate()

    if p.returncode:
        if re.match(r'Drive \d+ Full \(Storage Element \d+ loaded\)', err):
            logger.warning(
                'Tried to mount already mounted tape from {slot} to {drive} using {robot}'.format(
                    slot=slot, drive=drive, robot=robot
                )
            )
            raise TapeMountedError(err)

        logger.error(
            'Failed to mount tape from {slot} to {drive} using {robot}, err: {err}, returncode: {rcode}'.format(
                slot=slot, drive=drive, robot=robot, err=err, rcode=p.returncode
            )
        )
        raise RobotMountException('%s, return code: %s' % (err, p.returncode))

    logger.info('Mounted tape from {slot} to {drive} using {robot}'.format(slot=slot, drive=drive, robot=robot))
    return out


@retry(reraise=True, stop=stop_after_attempt(5), wait=wait_fixed(60))
def unmount_tape(robot, slot, drive):
    """
    Unmounts tape from drive into slot

    Args:
        robot: The device used to unmount the tape
        slot: Which slot to unload to
        drive: Which drive to load from
    """

    cmd = 'mtx -f %s unload %d %d' % (robot, slot, drive)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    logger.debug(
        'Unmounting tape from {drive} to {slot} using {robot}: {cmd}'.format(
            drive=drive, slot=slot, robot=robot, cmd=cmd
        )
    )
    out, err = p.communicate()

    if p.returncode:
        if re.match(r'Data Transfer Element \d+ is Empty', err):
            logger.warning(
                'Tried to unmount already unmounted tape from {drive} to {slot} using {robot}'.format(
                    drive=drive, slot=slot, robot=robot
                )
            )
            raise TapeUnmountedError(err)

        logger.error(
            'Failed to unmount tape from {drive} to {slot} using {robot}, err: {err}, returncode: {rcode}'.format(
                drive=drive, slot=slot, robot=robot, err=err, rcode=p.returncode
            )
        )
        raise RobotUnmountException('%s, return code: %s' % (err, p.returncode))

    logger.info('Unmounted tape from {drive} to {slot} using {robot}'.format(drive=drive, slot=slot, robot=robot))
    return out


def rewind_tape(drive):
    """
    Rewinds the tape in the given drive
    """

    cmd = 'mt -f %s rewind' % (drive)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)
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

    logger.debug('Rewinded tape in {drive}'.format(drive=drive))
    return out


def is_tape_drive_online(drive):
    """
    Checks if the given tape drive is online

    Args:
        drive: Which drive to check

    Returns:
        True if the drive is online, false otherwise
    """

    cmd = 'mt -f %s status' % drive
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)
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
    logger.debug('Waiting for {drive} to come online'.format(drive=drive))
    while timeout >= 0:
        if is_tape_drive_online(drive):
            return

        time.sleep(1)
        timeout -= 1

    logger.error('{drive} did not come online after {timeout} seconds'.format(drive=drive, timeout=120))
    raise RobotMountTimeoutException()


@retry(reraise=True, stop=stop_after_attempt(5), wait=wait_fixed(60))
def tape_empty(drive):
    logger.debug('Checking if tape in {drive} is empty'.format(drive=drive))
    try:
        logger.debug('Opening tape in {drive}'.format(drive=drive))
        tar = tarfile.open(drive, 'r|')
    except OSError as e:
        if e.errno == errno.EIO:
            logger.debug('I/O error while opening tape in {drive}, it is empty'.format(drive=drive))
            rewind_tape(drive)
            return True
        logger.exception('Unknown error while opening tape in {drive}'.format(drive=drive))
        raise
    except tarfile.ReadError as e:
        if str(e) == 'empty file':
            logger.debug('Empty file in tape in {drive}, tape is empty'.format(drive=drive))
            rewind_tape(drive)
            return True
        logger.exception('Unknown tarfile error while opening tape in {drive}'.format(drive=drive))
        raise
    else:
        logger.debug('Tape in {drive} is not empty'.format(drive=drive))
        tar.close()
        rewind_tape(drive)
        return False


def create_tape_label(medium, xmlpath):
    root = etree.Element('label')

    label_tape = etree.SubElement(root, 'tape')
    label_tape.set('id', medium.medium_id)

    local_create_date = localtime(medium.create_date)
    label_tape.set('date', local_create_date.replace(microsecond=0).isoformat())

    label_format = etree.SubElement(root, 'format')
    label_format.set('format', str(medium.storage_target.default_format))
    label_format.set('blocksize', str(medium.storage_target.default_block_size))
    label_format.set('drivemanufacture', str(medium.storage_target.type))

    tree = etree.ElementTree(root)
    tree.write(xmlpath, pretty_print=True, xml_declaration=True, encoding='UTF-8')


def verify_tape_label(medium, xmlstring):
    logger.debug('Verifying tape label of {medium} against {xml}'.format(medium=medium, xml=xmlstring))
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


def read_tape(device, path='.', block_size=DEFAULT_TAPE_BLOCK_SIZE):
    logger.info(
        'Extracting content from {device} to {path}, with block size {size}'.format(
            device=device, path=path, size=block_size
        )
    )
    with tarfile.open(device, 'r|', bufsize=block_size) as tar:
        tar.extractall(path)


def write_to_tape(device, paths, block_size=DEFAULT_TAPE_BLOCK_SIZE, arcname=None):
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

    if isinstance(paths, str):
        paths = [paths]

    logger.info(
        'Writing {paths} to {device} with block size {size}'.format(
            paths=",".join(paths), device=device, size=block_size
        )
    )

    if arcname is not None and len(paths) > 1:
        raise TypeError("'arcname' is not valid when write_to_tape is called with more than one path")

    with tarfile.open(device, 'w|', bufsize=block_size) as tar:
        for path in paths:
            if len(paths) > 1 or arcname is None:
                arcname = os.path.basename(os.path.normpath(path))

            tar.add(path, arcname)


def get_tape_file_number(drive):
    cmd = 'mt -f %s status | grep -i "file number"' % drive
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    logger.debug('Getting tape file number of {drive}: {cmd}'.format(drive=drive, cmd=cmd))
    out, err = p.communicate()

    if p.returncode:
        logger.error('Failed to get tape file number of {drive}'.format(drive=drive))

    if p.returncode == 1:
        raise MTInvalidOperationOrDeviceNameException(err)
    elif p.returncode == 2:
        raise MTFailedOperationException(err)

    file_number = int(out.split(',')[0].split('=')[1])
    logger.debug('Got {num} as file number of {drive}'.format(num=file_number, drive=drive))
    return file_number


def set_tape_file_number(drive, num=0):
    if num == 0:
        return rewind_tape(drive)

    current_num = get_tape_file_number(drive)

    new_num, op = get_tape_op_and_count(current_num, num)

    cmd = 'mt -f %s %s %d' % (drive, op, new_num)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    logger.debug('Setting file number of {drive} to {num}: {cmd}'.format(num=num, drive=drive, cmd=cmd))
    out, err = p.communicate()

    if p.returncode:
        logger.error('Failed to set tape file number of {drive} to {num}: {err}'.format(drive=drive, num=num, err=err))

    if p.returncode == 1:
        raise MTInvalidOperationOrDeviceNameException(err)
    elif p.returncode == 2:
        raise MTFailedOperationException(err)

    logger.debug('File number of {drive} set to {num}'.format(num=num, drive=drive))
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

    backend_name = settings.ESSARCH_TAPE_IDENTIFICATION_BACKEND
    backend = get_tape_identification_backend(backend_name)

    cmd = 'mtx -f %s status' % robot
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    logger.debug('Inventoring {robot}: {cmd}'.format(robot=robot, cmd=cmd))
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
                logger.debug(
                    'Drive {row} (drive_id={drive}, robot={robot}) found in database'.format(
                        row=row, drive=drive_id, robot=robot
                    )
                )

                if status == 'Full':
                    slot_id = dt_el[7]
                    medium_id = dt_el[10][:6]
                    backend.identify_tape(medium_id)

                    StorageMedium.objects.filter(
                        tape_slot__robot=robot, tape_slot__slot_id=slot_id, medium_id=medium_id
                    ).update(tape_drive=drive)
                else:
                    StorageMedium.objects.filter(tape_drive=drive).update(tape_drive=None)
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
                    medium_id = s_el[6][:6]
                    backend.identify_tape(medium_id)

                    slot, created = TapeSlot.objects.update_or_create(
                        robot=robot, slot_id=slot_id, defaults={'medium_id': medium_id}
                    )
                    if created:
                        logger.debug(
                            'Created tape slot with slot_id={slot}, medium_id={medium}'.format(
                                slot=slot_id, medium=medium_id
                            )
                        )
                    else:
                        logger.debug(
                            'Updated tape slot with slot_id={slot}, medium_id={medium}'.format(
                                slot=slot_id, medium=medium_id
                            )
                        )

                    StorageMedium.objects.filter(medium_id=medium_id).update(tape_slot=slot)
                else:
                    slot, created = TapeSlot.objects.get_or_create(robot=robot, slot_id=slot_id)
                    if created:
                        logger.debug('Created tape slot with slot_id={slot}'.format(slot=slot_id))
