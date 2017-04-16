import os
import tarfile

from subprocess import Popen, PIPE

from ESSArch_Core.storage.exceptions import (
    MTInvalidOperationOrDeviceNameException,
    MTFailedOperationException,
    RobotException,
    RobotMountException,
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


def read_tape(drive, path='.', block_size=DEFAULT_TAPE_BLOCK_SIZE):
    with tarfile.open(drive, 'r|', bufsize=block_size) as tar:
        tar.extractall(path)


def write_to_tape(drive, path, block_size=DEFAULT_TAPE_BLOCK_SIZE):
    """
    Writes content to a tape drive
    """

    basepath = os.path.basename(os.path.normpath(path))
    with tarfile.open(drive, 'w|', bufsize=block_size) as tar:
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
