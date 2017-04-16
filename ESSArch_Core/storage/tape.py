import errno
import os
import tarfile
import time

from subprocess import Popen, PIPE

from django.utils.timezone import localtime
from lxml import etree

from ESSArch_Core.storage.exceptions import (
    MTInvalidOperationOrDeviceNameException,
    MTFailedOperationException,
    RobotException,
    RobotMountException,
    RobotMountTimeoutException,
    RobotUnmountException
)

DEFAULT_TAPE_BLOCK_SIZE = 20*512


def mount_tape(robot, slot, drive):
    """
    Mounts tape from slot into drive

    Args:
        robot: The device used to mount the tape
        slot: Which slot to load from
        drive: Which drive to load to
    """

    cmd = 'mtx -f %s load %d %d' % (robot, slot, drive)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

    if p.returncode:
        raise RobotMountException('%s, return code: %s' % (err, p.returncode))

    return out


def unmount_tape(robot, slot, drive):
    """
    Unmounts tape from drive into slot

    Args:
        robot: The device used to unmount the tape
        slot: Which slot to unload to
        drive: Which drive to load from
    """

    cmd = 'mtx -f %s unload %d %d' % (robot, slot, drive)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

    if p.returncode:
        raise RobotUnmountException('%s, return code: %s' % (err, p.returncode))

    return out


def rewind_tape(drive):
    """
    Rewinds the tape in the given drive
    """

    cmd = 'mt -f %s rewind' % (drive)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

    if p.returncode == 1:
        raise MTInvalidOperationOrDeviceNameException(err)

    elif p.returncode == 2:
        raise MTFailedOperationException(err)

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
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

    if p.returncode:
        raise RobotException('%s, return code: %s' % (err, p.returncode))

    return 'ONLINE' in out


def wait_to_come_online(drive, timeout=120):
    while timeout >= 0:
        if is_tape_drive_online(drive):
            return

        time.sleep(1)
        timeout -= 1

    raise RobotMountTimeoutException()


def tape_empty(drive):
    try:
        with open(drive, 'rb') as f:
            f.read(20000)
    except IOError, e:
        if e.errno == errno.EIO:
            rewind_tape(drive)
            return True
        raise
    else:
        rewind_tape(drive)
        return False


def create_tape_label(medium, xmlpath):
    root = etree.Element('label')

    label_tape = etree.SubElement(root, 'tape')
    label_tape.set('id', medium.medium_id)

    local_create_date = localtime(medium.create_date)
    label_tape.set('date', local_create_date.replace(microsecond=0).isoformat())

    label_format = etree.SubElement(root, 'format')
    label_format.set('format', str(medium.format))
    label_format.set('blocksize', str(medium.block_size))
    label_format.set('drivemanufacture', str(medium.storage_target.type))

    tree = etree.ElementTree(root)
    tree.write(xmlpath, pretty_print=True, xml_declaration=True, encoding='UTF-8')


def verify_tape_label(medium, xmlstring):
    tree = etree.parse(xmlstring)
    root = tree.getroot()

    return root.find('label/tape')['id'] == str(medium.medium_id)


def read_tape(device, path='.', block_size=DEFAULT_TAPE_BLOCK_SIZE):
    with tarfile.open(device, 'r|', bufsize=block_size) as tar:
        tar.extractall(path)


def write_to_tape(device, path, block_size=DEFAULT_TAPE_BLOCK_SIZE):
    """
    Writes content to a tape drive
    """

    basepath = os.path.basename(os.path.normpath(path))
    with tarfile.open(device, 'w|', bufsize=block_size) as tar:
        tar.add(path, basepath)


def get_tape_file_number(drive):
    cmd = 'mt -f %s status | grep -i "file number"' % drive
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

    if p.returncode == 1:
        raise MTInvalidOperationOrDeviceNameException(err)

    elif p.returncode == 2:
        raise MTFailedOperationException(err)

    return int(out.split(',')[0].split('=')[1])


def set_tape_file_number(drive, num=0):
    if num == 0:
        return rewind_tape(drive)

    current_num = get_tape_file_number(drive)

    if num < current_num:
        op = 'bsfm'
        new_num = current_num - num + 1
    else:
        new_num = num - current_num

        if new_num > 0:
            op = 'fsf'
        elif new_num == 0:
            return

    cmd = 'mt -f %s %s %d' % (drive, op, new_num)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()

    if p.returncode == 1:
        raise MTInvalidOperationOrDeviceNameException(err)

    elif p.returncode == 2:
        raise MTFailedOperationException(err)

    return out
