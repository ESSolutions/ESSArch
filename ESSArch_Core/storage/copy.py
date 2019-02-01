import errno
import logging
import os
import time

from requests_toolbelt import MultipartEncoder
from retrying import retry
from os import walk

from ESSArch_Core.fixity.checksum import calculate_checksum

MB = 1024 * 1024

logger = logging.getLogger('essarch.storage.copy')


def copy_chunk_locally(src, dst, offset, file_size, block_size=65536):
    with open(src, 'rb') as srcf, open(dst, 'ab') as dstf:
        srcf.seek(offset)
        dstf.seek(offset)

        time_start = time.time()
        dstf.write(srcf.read(block_size))
        time_end = time.time()

        time_elapsed = time_end - time_start

        start = offset
        end = offset + block_size - 1
        if end > file_size:
            end = file_size - 1
        chunk_size = block_size / MB
        try:
            mb_per_sec = chunk_size / time_elapsed
        except ZeroDivisionError:
            mb_per_sec = chunk_size

        logger.info(
            'Copied chunk bytes %s - %s / %s from %s to %s at %s MB/Sec (%s sec)' % (
                start, end, file_size, src, dst, mb_per_sec, time_elapsed
            )
        )


def copy_chunk_remotely(src, dst, offset, file_size, requests_session, upload_id=None, block_size=65536):
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
    files = {'the_file': (filename, chunk)}

    response = requests_session.post(dst, data=data, files=files, headers=headers, timeout=60)
    response.raise_for_status()
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


def copy_chunk(src, dst, offset, file_size, requests_session=None, upload_id=None, block_size=65536):
    """
    Copies the given chunk to the given destination

    Args:
        src: The file to copy
        dst: Where the file should be copied to
        requests_session: The session to be used
        offset: The offset in the file
        block_size: Size of each block to copy
    Returns:
        None
    """

    def local(src, dst, offset, file_size, block_size=65536):
        return copy_chunk_locally(src, dst, offset, file_size, block_size=block_size)

    @retry(stop_max_attempt_number=5, wait_fixed=60000)
    def remote(src, dst, offset, file_size, requests_session, upload_id=None, block_size=65536):
        return copy_chunk_remotely(src, dst, offset, file_size,
                                   requests_session=requests_session, upload_id=upload_id,
                                   block_size=block_size)

    if requests_session is not None:
        if file_size is None:
            raise ValueError('file_size required on remote transfers')

        return remote(src, dst, offset, file_size, requests_session, upload_id, block_size)
    else:
        local(src, dst, offset, file_size, block_size=block_size)


def copy_file_locally(src, dst, block_size=65536):
    fsize = os.stat(src).st_size
    idx = 0

    directory = os.path.dirname(dst)

    try:
        os.makedirs(directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    open(dst, 'wb').close()  # remove content of destination if it exists

    while idx * block_size <= fsize:
        copy_chunk(src, dst, idx * block_size, fsize, block_size=block_size)
        idx += 1


def copy_file_remotely(src, dst, requests_session=None, block_size=65536):
    file_size = os.stat(src).st_size
    idx = 0

    upload_id = copy_chunk(src, dst, idx * block_size, file_size,
                           requests_session=requests_session, block_size=block_size)
    idx += 1

    while idx * block_size <= file_size:
        copy_chunk(src, dst, idx * block_size, requests_session=requests_session,
                   file_size=file_size, block_size=block_size, upload_id=upload_id)
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

    @retry(stop_max_attempt_number=5, wait_fixed=60000)
    def send_completion_request():
        response = requests_session.post(completion_url, data=m, headers=headers)
        response.raise_for_status()

    send_completion_request()


def copy_file(src, dst, requests_session=None, block_size=65536):
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
        copy_file_locally(src, dst, block_size=block_size)

    logger.info('Copied %s to %s' % (src, dst))
    return dst


def copy_dir(src, dst, requests_session=None, block_size=65536):
    for root, dirs, files in walk(src):
        for f in files:
            src_filepath = os.path.join(root, f)
            src_relpath = os.path.relpath(src_filepath, src)
            dst_filepath = os.path.join(dst, src_relpath)

            try:
                os.makedirs(os.path.dirname(dst_filepath))
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise

            copy_file(src_filepath, dst_filepath, requests_session=requests_session, block_size=block_size)

        for d in dirs:
            src_dir = os.path.join(root, d)
            src_relpath = os.path.relpath(src_dir, src)
            dst_dir = os.path.join(dst, src_relpath)
            try:
                os.makedirs(os.path.dirname(dst_dir))
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
    return dst


def copy(src, dst, requests_session=None, block_size=65536):
    if os.path.isfile(src):
        return copy_file(src, dst, requests_session=requests_session, block_size=block_size)

    return copy_dir(src, dst, requests_session=requests_session, block_size=block_size)
