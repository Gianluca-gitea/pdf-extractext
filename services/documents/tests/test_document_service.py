from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from bson.objectid import ObjectId

from app.services import document_service as document_service_module
from app.services.document_service import DocumentService, InvalidStatusTransitionError
from app.models import PublicDocument


def _make_mongo_doc(**overrides) -> dict:
    data = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "pdf_nombre": "doc.pdf",
        "txt_contenido": "texto",
        "txt_chars": 4,
        "checksum_archivo": "abc123",
        "checksum_algoritmo": "sha256",
        "estado": "pendiente",
        "error": None,
        "created_at": datetime.now(timezone.utc),
        "deleted_at": None,
        "duracion_ms": 100,
    }
    data.update(overrides)
    return data


def test_update_document_returns_none_when_missing() -> None:
    repository = MagicMock()
    repository.find_by_id.return_value = None
    service = DocumentService(repository=repository)

    result = service.update_document(ObjectId(), {"estado": "pendiente"})

    assert result is None


def test_update_document_allows_pendiente_to_ok() -> None:
    doc_id = ObjectId()
    repository = MagicMock()
    repository.find_by_id.return_value = _make_mongo_doc(_id=doc_id, estado="pendiente")
    repository.update_document.return_value = _make_mongo_doc(_id=doc_id, estado="ok")
    service = DocumentService(repository=repository)

    result = service.update_document(doc_id, {"estado": "ok"})

    assert isinstance(result, PublicDocument)
    assert result.estado == "ok"
    assert result.id == str(doc_id)
    repository.update_document.assert_called_once_with(doc_id, {"estado": "ok"})


def test_update_document_allows_pendiente_to_error() -> None:
    doc_id = ObjectId()
    repository = MagicMock()
    repository.find_by_id.return_value = _make_mongo_doc(_id=doc_id, estado="pendiente")
    repository.update_document.return_value = _make_mongo_doc(_id=doc_id, estado="error")
    service = DocumentService(repository=repository)

    result = service.update_document(doc_id, {"estado": "error"})

    assert isinstance(result, PublicDocument)
    assert result.estado == "error"
    repository.update_document.assert_called_once_with(doc_id, {"estado": "error"})


def test_update_document_allows_error_to_pendiente() -> None:
    doc_id = ObjectId()
    repository = MagicMock()
    repository.find_by_id.return_value = _make_mongo_doc(_id=doc_id, estado="error")
    repository.update_document.return_value = _make_mongo_doc(_id=doc_id, estado="pendiente")
    service = DocumentService(repository=repository)

    result = service.update_document(doc_id, {"estado": "pendiente"})

    assert isinstance(result, PublicDocument)
    assert result.estado == "pendiente"
    repository.update_document.assert_called_once_with(doc_id, {"estado": "pendiente"})


def test_update_document_rejects_error_to_ok() -> None:
    repository = MagicMock()
    repository.find_by_id.return_value = _make_mongo_doc(estado="error")
    service = DocumentService(repository=repository)

    with pytest.raises(InvalidStatusTransitionError):
        service.update_document(ObjectId(), {"estado": "ok"})


def test_update_document_rejects_ok_to_error() -> None:
    repository = MagicMock()
    repository.find_by_id.return_value = _make_mongo_doc(estado="ok")
    service = DocumentService(repository=repository)

    with pytest.raises(InvalidStatusTransitionError):
        service.update_document(ObjectId(), {"estado": "error"})


def test_update_document_rejects_invalid_estado() -> None:
    repository = MagicMock()
    repository.find_by_id.return_value = _make_mongo_doc(estado="pendiente")
    service = DocumentService(repository=repository)

    with pytest.raises(InvalidStatusTransitionError):
        service.update_document(ObjectId(), {"estado": "desconocido"})


def test_document_service_uses_shared_repository_by_default(monkeypatch) -> None:
    shared_repository = MagicMock()
    monkeypatch.setattr(
        document_service_module, "get_document_repository", lambda: shared_repository
    )

    assert DocumentService().repository is shared_repository


def test_get_document_by_id_returns_public_document() -> None:
    doc_id = ObjectId()
    repository = MagicMock()
    repository.find_by_id.return_value = _make_mongo_doc(_id=doc_id)
    service = DocumentService(repository=repository)

    result = service.get_document_by_id(doc_id, include_text=True)

    assert isinstance(result, PublicDocument)
    assert result.id == str(doc_id)
    repository.find_by_id.assert_called_once_with(doc_id, include_text=True)


def test_get_document_by_id_returns_none_when_missing() -> None:
    repository = MagicMock()
    repository.find_by_id.return_value = None
    service = DocumentService(repository=repository)

    result = service.get_document_by_id(ObjectId(), include_text=True)

    assert result is None


def test_get_document_by_checksum_returns_public_document() -> None:
    repository = MagicMock()
    repository.find_by_checksum.return_value = _make_mongo_doc()
    service = DocumentService(repository=repository)

    result = service.get_document_by_checksum("abc123")

    assert isinstance(result, PublicDocument)
    assert result.checksum_archivo == "abc123"
    repository.find_by_checksum.assert_called_once_with("abc123")


def test_get_document_by_checksum_returns_none_when_missing() -> None:
    repository = MagicMock()
    repository.find_by_checksum.return_value = None
    service = DocumentService(repository=repository)

    result = service.get_document_by_checksum("inexistente")

    assert result is None


def test_list_documents_returns_list_of_public_documents() -> None:
    repository = MagicMock()
    repository.list_documents.return_value = [
        _make_mongo_doc(_id=ObjectId(), pdf_nombre="doc1.pdf"),
        _make_mongo_doc(_id=ObjectId(), pdf_nombre="doc2.pdf"),
    ]
    service = DocumentService(repository=repository)

    result = service.list_documents(skip=0, limit=20, include_text=False)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(doc, PublicDocument) for doc in result)
    repository.list_documents.assert_called_once_with(skip=0, limit=20, include_text=False)


def test_list_documents_returns_empty_list() -> None:
    repository = MagicMock()
    repository.list_documents.return_value = []
    service = DocumentService(repository=repository)

    result = service.list_documents(skip=0, limit=20, include_text=False)

    assert result == []
