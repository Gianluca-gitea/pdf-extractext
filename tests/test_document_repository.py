from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from bson.objectid import ObjectId

from app.repositories.document_repository import DocumentRepository


class TestDocumentRepository:
    """Tests for MongoDB document repository."""

    @pytest.fixture
    def mock_collection(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_collection: MagicMock) -> DocumentRepository:
        mock_client = MagicMock()
        mock_db = MagicMock()

        mock_db.__getitem__.return_value = mock_collection
        mock_client.__getitem__.return_value = mock_db

        return DocumentRepository(mongo_client=mock_client)

    @pytest.fixture
    def valid_document(self) -> dict:
        return {
            "pdf_nombre": "test.pdf",
            "txt_contenido": "content",
            "txt_chars": 7,
            "checksum_archivo": "abc123",
            "checksum_algoritmo": "sha256",
            "estado": "ok",
            "error": None,
            "created_at": datetime.now(timezone.utc),
            "duracion_ms": 100,
        }

    def test_save_document_returns_inserted_id(
        self,
        repository: DocumentRepository,
        mock_collection: MagicMock,
        valid_document: dict,
    ) -> None:
        inserted_id = ObjectId()
        mock_collection.insert_one.return_value.inserted_id = inserted_id

        result = repository.save_document(valid_document)

        assert result == inserted_id

    def test_save_document_calls_insert_one(
        self,
        repository: DocumentRepository,
        mock_collection: MagicMock,
        valid_document: dict,
    ) -> None:
        repository.save_document(valid_document)

        mock_collection.insert_one.assert_called_once_with(valid_document)

    def test_find_document_by_id_returns_document(
        self,
        repository: DocumentRepository,
        mock_collection: MagicMock,
    ) -> None:
        doc_id = ObjectId()
        expected_document = {
            "_id": doc_id,
            "pdf_nombre": "test.pdf",
            "txt_contenido": "content",
            "checksum_archivo": "abc123",
        }

        mock_collection.find_one.return_value = expected_document

        result = repository.find_by_id(doc_id)

        assert result == expected_document
        mock_collection.find_one.assert_called_once_with({"_id": doc_id})

    def test_find_document_by_id_returns_none_if_not_found(
        self,
        repository: DocumentRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = None

        result = repository.find_by_id(ObjectId())

        assert result is None

    def test_find_by_checksum_returns_document(
        self,
        repository: DocumentRepository,
        mock_collection: MagicMock,
    ) -> None:
        checksum = "abcdef123456"
        expected_document = {
            "_id": ObjectId(),
            "pdf_nombre": "test.pdf",
            "checksum_archivo": checksum,
        }

        mock_collection.find_one.return_value = expected_document

        result = repository.find_by_checksum(checksum)

        assert result == expected_document
        mock_collection.find_one.assert_called_once_with(
            {"checksum_archivo": checksum}
        )

    def test_find_by_checksum_returns_none_if_not_found(
        self,
        repository: DocumentRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = None

        result = repository.find_by_checksum("nonexistent_checksum")

        assert result is None
