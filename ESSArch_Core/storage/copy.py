import logging
import os
import shutil
import time
from os import walk

from requests import RequestException
from requests_toolbelt import MultipartEncoder
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from ESSArch_Core.fixity.checksum import calculate_checksum

MB = 1024 * 1024
DEFAULT_BLOCK_SIZE = 10 * MB

logger = logging.getLogger('essarch.storage.copy')


@retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
       wait=wait_fixed(60), before_sleep=before_sleep_log(logger, logging.DEBUG))
def copy_chunk_remotely(src, dst, offset, file_size, requests_session, upload_id=None, block_size=DEFAULT_BLOCK_SIZE):
    filename = os.path.basename(src)

    with open(src, 'rb') as srcf:
        srcf.seek(offset)
        chunk = srcf.read(block_size)

    start = offset
    end = offset + block_size - 1

    if end > file_size:
        end = file_size - 1

    HTTP_CONTENT_RANGE = 'bytes %s-%s/%s' % (start, end, file_size)
    headers = {'Content-Range': HTTP_CONTENT_RANGE}

    data = {'upload_id': upload_id}
    files = {'file': (filename, chunk)}

    response = requests_session.post(dst, data=data, files=files, headers=headers, timeout=60)
    try:
        response.raise_for_status()
    except RequestException:
        logger.exception("Failed to copy chunk to {}: {}".format(dst, response.content))
        raise

    response_time = response.elapsed.total_seconds()
    request_size = (end - start) / MB
    try:
        mb_per_sec = request_size / response_time
    except ZeroDivisionError:
        mb_per_sec = request_size

    logger.info(
        'Copied chunk bytes %s - %s / %s from %s to %s at %s MB/Sec (%s sec)' % (
            start, end, file_size, src, dst, mb_per_sec, response_time
        )
    )

    return response.json()['upload_id']


def copy_file_locally(src, dst):
    fsize = os.stat(src).st_size

    directory = os.path.dirname(dst)
    os.makedirs(directory, exist_ok=True)

    time_start = time.time()
    shutil.copyfile(src, dst)
    time_end = time.time()

    time_elapsed = time_end - time_start

    fsize_mb = fsize / MB

    try:
        mb_per_sec = fsize_mb / time_elapsed
    except ZeroDivisionError:
        mb_per_sec = fsize_mb

    logger.info(
        'Copied {} ({} MB) to {} at {} MB/Sec ({} sec)'.format(
            src, fsize_mb, dst, mb_per_sec, time_elapsed
        )
    )


def copy_file_remotely(src, dst, requests_session=None, block_size=DEFAULT_BLOCK_SIZE):
    fsize = os.stat(src).st_size
    idx = 0

    time_start = time.time()
    upload_id = copy_chunk_remotely(src, dst, idx * block_size, requests_session=requests_session,
                                    file_size=fsize, block_size=block_size)
    idx += 1

    while idx * block_size <= fsize:
        copy_chunk_remotely(src, dst, idx * block_size, requests_session=requests_session,
                            file_size=fsize, block_size=block_size, upload_id=upload_id)
        idx += 1

    md5 = calculate_checksum(src, algorithm='MD5', block_size=block_size)

    completion_url = dst.rstrip('/') + '_complete/'

    m = MultipartEncoder(
        fields={
            'path': os.path.basename(src),
            'upload_id': upload_id,
            'md5': md5,
        }
    )
    headers = {'Content-Type': m.content_type}

    @retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
           wait=wait_fixed(60), before_sleep=before_sleep_log(logger, logging.DEBUG))
    def send_completion_request():
        response = requests_session.post(completion_url, data=m, headers=headers, timeout=60)
        response.raise_for_status()

    send_completion_request()

    time_end = time.time()
    time_elapsed = time_end - time_start

    fsize_mb = fsize / MB

    try:
        mb_per_sec = fsize_mb / time_elapsed
    except ZeroDivisionError:
        mb_per_sec = fsize_mb

    logger.info(
        'Copied {} ({} MB) to {} at {} MB/Sec ({} sec)'.format(
            src, fsize_mb, dst, mb_per_sec, time_elapsed
        )
    )


def copy_file(src, dst, requests_session=None, block_size=DEFAULT_BLOCK_SIZE):
    """
    Copies the given file to the given destination

    Args:
        src: The file to copy
        dst: Where the file should be copied to
        requests_session: The request session to be used
        block_size: Size of each block to copy
    Returns:
        None
    """

    if os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))

    logger.info('Copying %s to %s' % (src, dst))

    if requests_session is not None:
        copy_file_remotely(src, dst, requests_session, block_size=block_size)
    else:
        copy_file_locally(src, dst)

    return dst


def copy_dir(src, dst, requests_session=None, block_size=DEFAULT_BLOCK_SIZE):
    for root, dirs, files in walk(src):
        for f in files:
            src_filepath = os.path.join(root, f)
            src_relpath = os.path.relpath(src_filepath, src)
            dst_filepath = os.path.join(dst, src_relpath)

            os.makedirs(os.path.dirname(dst_filepath), exist_ok=True)
            copy_file(src_filepath, dst_filepath, requests_session=requests_session, block_size=block_size)

        for d in dirs:
            src_dir = os.path.join(root, d)
            src_relpath = os.path.relpath(src_dir, src)
            dst_dir = os.path.join(dst, src_relpath)
            os.makedirs(os.path.dirname(dst_dir), exist_ok=True)
    return dst


def copy(src, dst, requests_session=None, block_size=DEFAULT_BLOCK_SIZE):
    if os.path.isfile(src):
        return copy_file(src, dst, requests_session=requests_session, block_size=block_size)

    return copy_dir(src, dst, requests_session=requests_session, block_size=block_size)
