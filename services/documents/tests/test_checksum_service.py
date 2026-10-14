import hashlib

from app.services.checksum_service import calc_checksum


class TestChecksumService:
    """Tests for checksum calculation service."""

    def test_calc_checksum_returns_sha256_checksum(self) -> None:
        file_bytes = b"test content"
        expected_checksum = hashlib.sha256(file_bytes).hexdigest()

        result = calc_checksum(file_bytes)

        assert result == expected_checksum

    def test_calc_checksum_is_consistent_for_same_content(self) -> None:
        file_bytes = b"consistent content"

        checksum_1 = calc_checksum(file_bytes)
        checksum_2 = calc_checksum(file_bytes)

        assert checksum_1 == checksum_2

    def test_calc_checksum_differs_for_different_content(self) -> None:
        checksum_1 = calc_checksum(b"content one")
        checksum_2 = calc_checksum(b"content two")

        assert checksum_1 != checksum_2

    def test_calc_checksum_handles_empty_bytes(self) -> None:
        file_bytes = b""
        expected_checksum = hashlib.sha256(file_bytes).hexdigest()

        result = calc_checksum(file_bytes)

        assert result == expected_checksum

    def test_calc_checksum_handles_binary_data(self) -> None:
        file_bytes = bytes(range(256))
        expected_checksum = hashlib.sha256(file_bytes).hexdigest()

        result = calc_checksum(file_bytes)

        assert result == expected_checksum
