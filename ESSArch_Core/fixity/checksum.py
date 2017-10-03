from __future__ import division

import logging
import os
import time

from ESSArch_Core.util import alg_from_str

MB = 1024*1024

logger = logging.getLogger('essarch.fixity.checksum')


def calculate_checksum(filename, algorithm='SHA-256', block_size=65536):
    """
    Calculates the checksum for the given file, one chunk at a time

    Args:
        filename: The filename to calculate checksum for
        block_size: The size of the chunk to calculate
        algorithm: The algorithm to use

    Returns:
        The hexadecimal digest of the checksum
    """

    hash_val = alg_from_str(algorithm)()

    if os.name == 'nt':
        start_time = time.clock()
    else:
        start_time = time.time()

    with open(filename, 'r') as f:
        while True:
            data = f.read(block_size)
            if data:
                hash_val.update(data)
            else:
                break

    if os.name == 'nt':
        end_time = time.clock()
    else:
        end_time = time.time()

    time_elapsed = end_time - start_time
    size = os.path.getsize(filename)
    size_mb = size / MB

    try:
        mb_per_sec = size_mb / time_elapsed
    except ZeroDivisionError:
        mb_per_sec = size_mb

    digest = hash_val.hexdigest()
    logger.info("Calculated checksum for %s with %s at %s MB/Sec (%s sec): %s" % (filename, algorithm, mb_per_sec, time_elapsed, digest))

    return digest
