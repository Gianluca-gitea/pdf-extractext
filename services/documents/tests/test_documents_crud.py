from datetime import datetime, timezone
from unittest.mock import MagicMock

from bson.objectid import ObjectId
from fastapi.testclient import TestClient

from app import main as main_module
from app.models import PublicDocument, DocumentResponse, DocumentList
from app.routes import documents as document_routes
from app.services.document_service import InvalidStatusTransitionError

client = TestClient(main_module.app)


def _make_public_document(**overrides) -> PublicDocument:
    data = {
        "id": "507f1f77bcf86cd799439011",
        "pdf_nombre": "doc.pdf",
        "txt_contenido": "texto",
        "txt_chars": 4,
        "checksum_archivo": "abc123",
        "checksum_algoritmo": "sha256",
        "estado": "ok",
        "error": None,
        "created_at": "2024-01-01T00:00:00+00:00",
        "deleted_at": None,
        "duracion_ms": 100,
    }
    data.update(overrides)
    return PublicDocument(**data)


def test_list_documents_returns_serialized_items(monkeypatch) -> None:
    document_id = "507f1f77bcf86cd799439011"
    service = MagicMock()
    service.list_documents.return_value = [
        _make_public_document(id=document_id, pdf_nombre="doc.pdf")
    ]
    monkeypatch.setattr(document_routes, "DocumentService", lambda: service)

    response = client.get("/documents")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["_id"] == document_id
    service.list_documents.assert_called_once_with(skip=0, limit=20, include_text=False)


def test_list_documents_respects_query_params(monkeypatch) -> None:
    service = MagicMock()
    service.list_documents.return_value = []
    monkeypatch.setattr(document_routes, "DocumentService", lambda: service)

    response = client.get("/documents?skip=5&limit=10&include_text=true")

    assert response.status_code == 200
    service.list_documents.assert_called_once_with(skip=5, limit=10, include_text=True)


def test_list_documents_serializes_datetime(monkeypatch) -> None:
    document_id = "507f1f77bcf86cd799439011"
    created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    service = MagicMock()
    service.list_documents.return_value = [
        _make_public_document(
            id=document_id,
            created_at=created_at,
        )
    ]
    monkeypatch.setattr(document_routes, "DocumentService", lambda: service)

    response = client.get("/documents")

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["created_at"].startswith("2024-01-01T00:00:00")


def test_get_document_by_id_returns_document(monkeypatch) -> None:
    document_id = "507f1f77bcf86cd799439011"
    service = MagicMock()
    service.get_document_by_id.return_value = _make_public_document(
        id=document_id, pdf_nombre="doc.pdf"
    )
    monkeypatch.setattr(document_routes, "DocumentService", lambda: service)

    response = client.get(f"/documents/{document_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["document"]["_id"] == document_id
    service.get_document_by_id.assert_called_once_with(ObjectId(document_id), include_text=True)


def test_get_document_by_id_excludes_text_when_requested(monkeypatch) -> None:
    document_id = "507f1f77bcf86cd799439011"
    service = MagicMock()
    service.get_document_by_id.return_value = _make_public_document(
        id=document_id, pdf_nombre="doc.pdf"
    )
    monkeypatch.setattr(document_routes, "DocumentService", lambda: service)

    response = client.get(f"/documents/{document_id}?include_text=false")

    assert response.status_code == 200
    service.get_document_by_id.assert_called_once_with(ObjectId(document_id), include_text=False)


def test_get_document_by_id_returns_404_when_missing(monkeypatch) -> None:
    service = MagicMock()
    service.get_document_by_id.return_value = None
    monkeypatch.setattr(document_routes, "DocumentService", lambda: service)

    response = client.get("/documents/507f1f77bcf86cd799439011")

    assert response.status_code == 404
    assert response.json() == {"detail": "Documento no encontrado."}


def test_get_document_by_id_rejects_invalid_id() -> None:
    response = client.get("/documents/id-invalido")

    assert response.status_code == 400
    assert response.json() == {"detail": document_routes.INVALID_DOCUMENT_ID_ERROR_DETAIL}


def test_update_document_updates_fields(monkeypatch) -> None:
    document_id = "507f1f77bcf86cd799439011"
    service = MagicMock()
    service.update_document.return_value = _make_public_document(
        id=document_id, pdf_nombre="nuevo.pdf", estado="ok"
    )
    monkeypatch.setattr(document_routes, "DocumentService", lambda: service)

    response = client.patch(
        f"/documents/{document_id}",
        json={"pdf_nombre": "nuevo.pdf", "estado": "ok"},
    )

    assert response.status_code == 200
    service.update_document.assert_called_once_with(
        ObjectId(document_id),
        {"pdf_nombre": "nuevo.pdf", "estado": "ok"},
    )


def test_update_document_rejects_empty_payload(monkeypatch) -> None:
    service = MagicMock()
    service.update_document.return_value = None
    monkeypatch.setattr(document_routes, "DocumentService", lambda: service)

    response = client.patch("/documents/507f1f77bcf86cd799439011", json={})

    assert response.status_code == 400
    assert response.json() == {"detail": document_routes.NO_UPDATE_FIELDS_ERROR_DETAIL}


def test_update_document_returns_404_when_missing(monkeypatch) -> None:
    service = MagicMock()
    service.update_document.return_value = None
    monkeypatch.setattr(document_routes, "DocumentService", lambda: service)

    response = client.patch(
        "/documents/507f1f77bcf86cd799439011",
        json={"estado": "ok"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Documento no encontrado."}


def test_update_document_rejects_invalid_status_transition(monkeypatch) -> None:
    service = MagicMock()
    service.update_document.side_effect = InvalidStatusTransitionError(
        "Transicion de estado invalida: error -> ok"
    )
    monkeypatch.setattr(document_routes, "DocumentService", lambda: service)

    response = client.patch(
        "/documents/507f1f77bcf86cd799439011",
        json={"estado": "ok"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Transicion de estado invalida: error -> ok"}


def test_update_document_rejects_invalid_id() -> None:
    response = client.patch("/documents/id-invalido", json={"estado": "ok"})

    assert response.status_code == 400
    assert response.json() == {"detail": document_routes.INVALID_DOCUMENT_ID_ERROR_DETAIL}


def test_update_document_rejects_invalid_estado_schema() -> None:
    response = client.patch(
        "/documents/507f1f77bcf86cd799439011",
        json={"estado": "desconocido"},
    )

    assert response.status_code == 422


def test_delete_document_returns_deleted_status(monkeypatch) -> None:
    service = MagicMock()
    service.delete_document.return_value = True
    monkeypatch.setattr(document_routes, "DocumentService", lambda: service)

    response = client.delete("/documents/507f1f77bcf86cd799439011")

    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}


def test_delete_document_returns_404_when_missing(monkeypatch) -> None:
    service = MagicMock()
    service.delete_document.return_value = False
    monkeypatch.setattr(document_routes, "DocumentService", lambda: service)

    response = client.delete("/documents/507f1f77bcf86cd799439011")

    assert response.status_code == 404
    assert response.json() == {"detail": "Documento no encontrado."}


def test_delete_document_rejects_invalid_id() -> None:
    response = client.delete("/documents/id-invalido")

    assert response.status_code == 400
    assert response.json() == {"detail": document_routes.INVALID_DOCUMENT_ID_ERROR_DETAIL}


def test_download_document_text_returns_txt_attachment(monkeypatch) -> None:
    """Test para GET /documents/{id}/download con PublicDocument."""
    document_id = "507f1f77bcf86cd799439011"
    service = MagicMock()
    service.get_document_by_id.return_value = _make_public_document(
        id=document_id,
        pdf_nombre="documento.pdf",
        txt_contenido="texto descargable",
    )
    monkeypatch.setattr(document_routes, "DocumentService", lambda: service)

    response = client.get(f"/documents/{document_id}/download")

    assert response.status_code == 200
    assert response.text == "texto descargable"
    assert response.headers["content-disposition"] == 'attachment; filename="documento.pdf.txt"'
    assert response.headers["content-type"].startswith("text/plain")
