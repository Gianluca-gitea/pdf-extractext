import hashlib


def calc_checksum(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()
