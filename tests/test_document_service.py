from unittest.mock import MagicMock

import pytest
from bson.objectid import ObjectId

from app.services.document_service import DocumentService, InvalidStatusTransitionError


def test_update_document_returns_none_when_missing() -> None:
    repository = MagicMock()
    repository.find_by_id.return_value = None
    service = DocumentService(repository=repository)

    result = service.update_document(ObjectId(), {"estado": "pendiente"})

    assert result is None


def test_update_document_allows_pendiente_to_ok() -> None:
    doc_id = ObjectId()
    repository = MagicMock()
    repository.find_by_id.return_value = {"_id": doc_id, "estado": "pendiente"}
    repository.update_document.return_value = {"_id": doc_id, "estado": "ok"}
    service = DocumentService(repository=repository)

    result = service.update_document(doc_id, {"estado": "ok"})

    assert result["estado"] == "ok"
    repository.update_document.assert_called_once_with(doc_id, {"estado": "ok"})


def test_update_document_allows_pendiente_to_error() -> None:
    doc_id = ObjectId()
    repository = MagicMock()
    repository.find_by_id.return_value = {"_id": doc_id, "estado": "pendiente"}
    repository.update_document.return_value = {"_id": doc_id, "estado": "error"}
    service = DocumentService(repository=repository)

    result = service.update_document(doc_id, {"estado": "error"})

    assert result["estado"] == "error"
    repository.update_document.assert_called_once_with(doc_id, {"estado": "error"})


def test_update_document_allows_error_to_pendiente() -> None:
    doc_id = ObjectId()
    repository = MagicMock()
    repository.find_by_id.return_value = {"_id": doc_id, "estado": "error"}
    repository.update_document.return_value = {"_id": doc_id, "estado": "pendiente"}
    service = DocumentService(repository=repository)

    result = service.update_document(doc_id, {"estado": "pendiente"})

    assert result["estado"] == "pendiente"
    repository.update_document.assert_called_once_with(doc_id, {"estado": "pendiente"})


def test_update_document_rejects_error_to_ok() -> None:
    repository = MagicMock()
    repository.find_by_id.return_value = {"_id": ObjectId(), "estado": "error"}
    service = DocumentService(repository=repository)

    with pytest.raises(InvalidStatusTransitionError):
        service.update_document(ObjectId(), {"estado": "ok"})


def test_update_document_rejects_ok_to_error() -> None:
    repository = MagicMock()
    repository.find_by_id.return_value = {"_id": ObjectId(), "estado": "ok"}
    service = DocumentService(repository=repository)

    with pytest.raises(InvalidStatusTransitionError):
        service.update_document(ObjectId(), {"estado": "error"})


def test_update_document_rejects_invalid_estado() -> None:
    repository = MagicMock()
    repository.find_by_id.return_value = {"_id": ObjectId(), "estado": "pendiente"}
    service = DocumentService(repository=repository)

    with pytest.raises(InvalidStatusTransitionError):
        service.update_document(ObjectId(), {"estado": "desconocido"})
