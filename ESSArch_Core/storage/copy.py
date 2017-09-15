import errno
import logging
import os

from requests_toolbelt import MultipartEncoder

from retrying import retry

from ESSArch_Core.fixity.checksum import calculate_checksum


logger = logging.getLogger('essarch.storage.copy')

def copy_chunk_locally(src, dst, offset, block_size=65536):
    with open(src, 'r') as srcf, open(dst, 'a') as dstf:
        srcf.seek(offset)
        dstf.seek(offset)

        dstf.write(srcf.read(block_size))


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
    response = requests_session.post(dst, data=data, files=files, headers=headers)
    response.raise_for_status()

    return response.json()['upload_id']


def copy_chunk(src, dst, offset, file_size=None, requests_session=None, upload_id=None, block_size=65536):
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

    def local(src, dst, offset, block_size=65536):
        return copy_chunk_locally(src, dst, offset, block_size)

    @retry(stop_max_attempt_number=5, wait_fixed=60000)
    def remote(src, dst, offset, file_size, requests_session, upload_id=None, block_size=65536):
        return copy_chunk_remotely(src, dst, offset, file_size=file_size,
                                   requests_session=requests_session, upload_id=upload_id,
                                   block_size=block_size)

    if requests_session is not None:
        if file_size is None:
            raise ValueError('file_size required on remote transfers')

        return remote(src, dst, offset, file_size, requests_session, upload_id, block_size)
    else:
        local(src, dst, offset, block_size)


def copy_file_locally(src, dst, block_size=65536):
    fsize = os.stat(src).st_size
    idx = 0

    directory = os.path.dirname(dst)

    try:
        os.makedirs(directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    open(dst, 'w').close()  # remove content of destination if it exists

    while idx*block_size <= fsize:
        copy_chunk(src, dst, idx*block_size, block_size=block_size)
        idx += 1


def copy_file_remotely(src, dst, requests_session=None, block_size=65536):
    file_size = os.stat(src).st_size
    idx = 0

    upload_id = copy_chunk(src, dst, idx*block_size, requests_session=requests_session,
                           file_size=file_size, block_size=block_size)
    idx += 1

    while idx*block_size <= file_size:
        copy_chunk(src, dst, idx*block_size, requests_session=requests_session,
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

