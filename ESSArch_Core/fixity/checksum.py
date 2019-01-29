from __future__ import division, unicode_literals

import hashlib
import logging
import os
import time

MB = 1024 * 1024

logger = logging.getLogger('essarch.fixity.checksum')


def alg_from_str(algname):
    valid = {
        "MD5": hashlib.md5,
        "SHA-1": hashlib.sha1,
        "SHA-224": hashlib.sha224,
        "SHA-256": hashlib.sha256,
        "SHA-384": hashlib.sha384,
        "SHA-512": hashlib.sha512
    }

    try:
        return valid[algname.upper()]
    except KeyError:
        raise KeyError("Algorithm %s does not exist" % algname)


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

    logger.debug("Calculaing checksum for %s with %s ..." % (filename, algorithm))

    with open(filename, 'rb') as f:
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
    logger.info(
        "Calculated checksum for %s with %s at %s MB/Sec (%s sec): %s" % (
            filename, algorithm, mb_per_sec, time_elapsed, digest
        )
    )

    return digest
