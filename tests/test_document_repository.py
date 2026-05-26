from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from bson.objectid import ObjectId
from pymongo import ReturnDocument

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
            "deleted_at": None,
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
        mock_collection.find_one.assert_called_once_with(
            {
                "$and": [
                    {"_id": doc_id},
                    {"$or": [{"deleted_at": None}, {"deleted_at": {"$exists": False}}]},
                ]
            },
            None,
        )

    def test_find_document_by_id_returns_none_if_not_found(
        self,
        repository: DocumentRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = None

        result = repository.find_by_id(ObjectId())

        assert result is None

    def test_find_document_by_id_excludes_text_when_requested(
        self,
        repository: DocumentRepository,
        mock_collection: MagicMock,
    ) -> None:
        doc_id = ObjectId()

        repository.find_by_id(doc_id, include_text=False)

        mock_collection.find_one.assert_called_once_with(
            {
                "$and": [
                    {"_id": doc_id},
                    {"$or": [{"deleted_at": None}, {"deleted_at": {"$exists": False}}]},
                ]
            },
            {"txt_contenido": 0},
        )

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
            {
                "$and": [
                    {"checksum_archivo": checksum},
                    {"$or": [{"deleted_at": None}, {"deleted_at": {"$exists": False}}]},
                ]
            }
        )

    def test_find_by_checksum_returns_none_if_not_found(
        self,
        repository: DocumentRepository,
        mock_collection: MagicMock,
    ) -> None:
        mock_collection.find_one.return_value = None

        result = repository.find_by_checksum("nonexistent_checksum")

        assert result is None

    def test_list_documents_excludes_text_by_default(
        self,
        repository: DocumentRepository,
        mock_collection: MagicMock,
    ) -> None:
        doc_id = ObjectId()
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.skip.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.__iter__.return_value = iter([
            {"_id": doc_id, "pdf_nombre": "test.pdf"}
        ])
        mock_collection.find.return_value = cursor

        result = repository.list_documents()

        mock_collection.find.assert_called_once_with(
            {"$or": [{"deleted_at": None}, {"deleted_at": {"$exists": False}}]},
            {"txt_contenido": 0},
        )
        assert result == [{"_id": doc_id, "pdf_nombre": "test.pdf"}]

    def test_list_documents_includes_text_when_requested(
        self,
        repository: DocumentRepository,
        mock_collection: MagicMock,
    ) -> None:
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.skip.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.__iter__.return_value = iter([
            {"_id": ObjectId(), "pdf_nombre": "test.pdf", "txt_contenido": "text"}
        ])
        mock_collection.find.return_value = cursor

        repository.list_documents(include_text=True)

        mock_collection.find.assert_called_once_with(
            {"$or": [{"deleted_at": None}, {"deleted_at": {"$exists": False}}]},
            None,
        )

    def test_update_document_calls_find_one_and_update(
        self,
        repository: DocumentRepository,
        mock_collection: MagicMock,
    ) -> None:
        doc_id = ObjectId()
        updates = {"estado": "ok"}
        updated_document = {"_id": doc_id, "estado": "ok"}
        mock_collection.find_one_and_update.return_value = updated_document

        result = repository.update_document(doc_id, updates)

        mock_collection.find_one_and_update.assert_called_once_with(
            {
                "$and": [
                    {"_id": doc_id},
                    {"$or": [{"deleted_at": None}, {"deleted_at": {"$exists": False}}]},
                ]
            },
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
        assert result == updated_document

    def test_delete_document_returns_true_on_success(
        self,
        repository: DocumentRepository,
        mock_collection: MagicMock,
    ) -> None:
        doc_id = ObjectId()
        mock_collection.find_one_and_update.return_value = {"_id": doc_id}

        result = repository.delete_document(doc_id)

        args, kwargs = mock_collection.find_one_and_update.call_args
        assert args[0] == {
            "$and": [
                {"_id": doc_id},
                {"$or": [{"deleted_at": None}, {"deleted_at": {"$exists": False}}]},
            ]
        }
        assert "deleted_at" in args[1]["$set"]
        assert kwargs["return_document"] == ReturnDocument.AFTER
        assert result is True
