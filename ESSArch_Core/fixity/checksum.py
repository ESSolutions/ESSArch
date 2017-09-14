import logging

from ESSArch_Core.util import alg_from_str


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

    logger.info("Calculating checksum for %s with %s" % (filename, algorithm))

    with open(filename, 'r') as f:
        while True:
            data = f.read(block_size)
            if data:
                hash_val.update(data)
            else:
                break

    digest = hash_val.hexdigest()
    logger.info("Calculated checksum for %s with %s: %s" % (filename, algorithm, digest))

    return digest
