import errno
import logging
import os
import shutil
import time
from pathlib import Path

from django.conf import settings

from ESSArch_Core.storage.exceptions import NoSpaceLeftError
from ESSArch_Core.util import (
    get_tree_size_and_count,
    pretty_mb_per_sec,
    pretty_size,
    pretty_time_to_sec,
)

MB = 1024 * 1024


def enough_space_available(dst: str, src: str, raise_exception: bool = False, src_size: int = 0) -> bool:
    """
    Tells if there is enough space available at path dst for src to be copied there

    :param src: Path to be copied
    :param dst: Destination
    :param raise_exception: Raises exception if set to true and enough space is not available
    :return: True if src can be copied to dst, else False
    """

    if src_size == 0:
        src_size, _ = get_tree_size_and_count(src)
    dst_free_space = shutil.disk_usage(dst).free

    try:
        assert src_size <= dst_free_space - getattr(settings, 'ESSARCH_MINIMUM_FREE_DISK_SPACE', 0)
    except AssertionError:
        if raise_exception:
            raise NoSpaceLeftError(f'Not enough space available for {src} at {dst}')
        return False
    return True


def move_file(src, dst):
    """
    Moves the given file to the given destination

    Args:
        src: The file to move
        dst: Where the file should be moved to
    Returns:
        None
    """

    logger = logging.getLogger('essarch.storage.util.move')
    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))

    logger.info('Moving %s to %s' % (src, dst))

    try:
        enough_space_available(os.path.dirname(dst), src, True)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        enough_space_available(os.path.dirname(dst), src, True)

    if os.path.isdir(dst):
        real_dst = os.path.join(dst, shutil._basename(src))
        if os.path.exists(real_dst):
            os.remove(real_dst)

    fsize = os.stat(src).st_size
    time_start = time.time()
    shutil.move(src, dst)
    time_end = time.time()

    time_elapsed = time_end - time_start
    fsize_mb = fsize / MB
    try:
        mb_per_sec = fsize_mb / time_elapsed
    except ZeroDivisionError:
        mb_per_sec = fsize_mb

    logger.info(
        'Moved {} ({}) to {} at {} MB/Sec ({} sec)'.format(
            src, pretty_size(fsize), dst, pretty_mb_per_sec(mb_per_sec), pretty_time_to_sec(time_elapsed)
        )
    )

    return dst


def move_dir(src, dst):
    logger = logging.getLogger('essarch.storage.util.move')
    if os.path.isfile(dst):
        raise ValueError(f'Cannot overwrite non-directory {dst} with directory {src}')

    logger.info('Moving %s to %s' % (src, dst))

    root_directory = Path(src)
    dirsize = sum(f.stat().st_size for f in root_directory.glob('**/*') if f.is_file())

    try:
        enough_space_available(dst, src, True, dirsize)
    except FileNotFoundError:
        os.makedirs(dst, exist_ok=True)
        enough_space_available(dst, src, True, dirsize)

    time_start = time.time()
    shutil.move(src, dst)
    time_end = time.time()

    time_elapsed = time_end - time_start
    dirsize_mb = dirsize / MB
    try:
        mb_per_sec = dirsize_mb / time_elapsed
    except ZeroDivisionError:
        mb_per_sec = dirsize_mb

    logger.info(
        'Moved {} ({}) to {} at {} MB/Sec ({} sec)'.format(
            src, pretty_size(dirsize), dst, pretty_mb_per_sec(mb_per_sec), pretty_time_to_sec(time_elapsed)
        )
    )

    return dst


def move(src, dst):
    if src is None:
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), src)
    elif os.path.isfile(src):
        return move_file(src, dst)
    elif os.path.isdir(src):
        return move_dir(src, dst)
    else:
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), src)
