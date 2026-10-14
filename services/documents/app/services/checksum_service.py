import hashlib
import logging

logger = logging.getLogger(__name__)


def calc_checksum(file_bytes: bytes) -> str:
    logger.debug("Calculating checksum for payload size_bytes=%d", len(file_bytes))
    result = hashlib.sha256(file_bytes).hexdigest()
    logger.debug("Checksum calculated successfully")
    return result
