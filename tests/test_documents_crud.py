from datetime import datetime, timezone
from unittest.mock import MagicMock

from bson.objectid import ObjectId
from fastapi.testclient import TestClient

from app import main as main_module
from app.dependencies import get_document_service
from app.services.document_service import DocumentService, InvalidStatusTransitionError


def _override_service(service: DocumentService):
    main_module.app.dependency_overrides[get_document_service] = lambda: service


def _clear_overrides():
    main_module.app.dependency_overrides.clear()


client = TestClient(main_module.app)


def test_list_documents_returns_serialized_items() -> None:
    document_id = ObjectId("507f1f77bcf86cd799439011")
    service = MagicMock()
    service.list_documents.return_value = [
        {
            "_id": document_id,
            "pdf_nombre": "doc.pdf",
        }
    ]
    _override_service(service)

    response = client.get("/documents")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["_id"] == "507f1f77bcf86cd799439011"
    service.list_documents.assert_called_once_with(skip=0, limit=20, include_text=False)
    _clear_overrides()


def test_list_documents_respects_query_params() -> None:
    service = MagicMock()
    service.list_documents.return_value = []
    _override_service(service)

    response = client.get("/documents?skip=5&limit=10&include_text=true")

    assert response.status_code == 200
    service.list_documents.assert_called_once_with(skip=5, limit=10, include_text=True)
    _clear_overrides()


def test_list_documents_serializes_datetime() -> None:
    document_id = ObjectId("507f1f77bcf86cd799439011")
    created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    service = MagicMock()
    service.list_documents.return_value = [
        {
            "_id": document_id,
            "created_at": created_at,
        }
    ]
    _override_service(service)

    response = client.get("/documents")

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["created_at"].startswith("2024-01-01T00:00:00")
    _clear_overrides()


def test_get_document_by_id_returns_document() -> None:
    document_id = ObjectId("507f1f77bcf86cd799439011")
    service = MagicMock()
    service.get_document_by_id.return_value = {
        "_id": document_id,
        "pdf_nombre": "doc.pdf",
    }
    _override_service(service)

    response = client.get(f"/documents/{document_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["document"]["_id"] == "507f1f77bcf86cd799439011"
    service.get_document_by_id.assert_called_once_with(document_id, include_text=True)
    _clear_overrides()


def test_get_document_by_id_excludes_text_when_requested() -> None:
    document_id = ObjectId("507f1f77bcf86cd799439011")
    service = MagicMock()
    service.get_document_by_id.return_value = {
        "_id": document_id,
        "pdf_nombre": "doc.pdf",
    }
    _override_service(service)

    response = client.get(f"/documents/{document_id}?include_text=false")

    assert response.status_code == 200
    service.get_document_by_id.assert_called_once_with(document_id, include_text=False)
    _clear_overrides()


def test_get_document_by_id_returns_404_when_missing() -> None:
    service = MagicMock()
    service.get_document_by_id.return_value = None
    _override_service(service)

    response = client.get("/documents/507f1f77bcf86cd799439011")

    assert response.status_code == 404
    assert response.json() == {"detail": "Documento no encontrado."}
    _clear_overrides()


def test_get_document_by_id_rejects_invalid_id() -> None:
    service = MagicMock()
    _override_service(service)

    response = client.get("/documents/id-invalido")

    assert response.status_code == 400
    assert response.json() == {"detail": main_module.INVALID_DOCUMENT_ID_ERROR_DETAIL}
    _clear_overrides()


def test_update_document_updates_fields() -> None:
    document_id = ObjectId("507f1f77bcf86cd799439011")
    service = MagicMock()
    service.update_document.return_value = {
        "_id": document_id,
        "pdf_nombre": "nuevo.pdf",
        "estado": "ok",
    }
    _override_service(service)

    response = client.patch(
        f"/documents/{document_id}",
        json={"pdf_nombre": "nuevo.pdf", "estado": "ok"},
    )

    assert response.status_code == 200
    service.update_document.assert_called_once_with(
        document_id,
        {"pdf_nombre": "nuevo.pdf", "estado": "ok"},
    )
    _clear_overrides()


def test_update_document_rejects_empty_payload() -> None:
    service = MagicMock()
    service.update_document.return_value = None
    _override_service(service)

    response = client.patch("/documents/507f1f77bcf86cd799439011", json={})

    assert response.status_code == 400
    assert response.json() == {"detail": main_module.NO_UPDATE_FIELDS_ERROR_DETAIL}
    _clear_overrides()


def test_update_document_returns_404_when_missing() -> None:
    service = MagicMock()
    service.update_document.return_value = None
    _override_service(service)

    response = client.patch(
        "/documents/507f1f77bcf86cd799439011",
        json={"estado": "ok"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Documento no encontrado."}
    _clear_overrides()


def test_update_document_rejects_invalid_status_transition() -> None:
    service = MagicMock()
    service.update_document.side_effect = InvalidStatusTransitionError(
        "Transicion de estado invalida: error -> ok"
    )
    _override_service(service)

    response = client.patch(
        "/documents/507f1f77bcf86cd799439011",
        json={"estado": "ok"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Transicion de estado invalida: error -> ok"}
    _clear_overrides()


def test_update_document_rejects_invalid_id() -> None:
    service = MagicMock()
    _override_service(service)

    response = client.patch("/documents/id-invalido", json={"estado": "ok"})

    assert response.status_code == 400
    assert response.json() == {"detail": main_module.INVALID_DOCUMENT_ID_ERROR_DETAIL}
    _clear_overrides()


def test_update_document_rejects_invalid_estado_schema() -> None:
    service = MagicMock()
    _override_service(service)

    response = client.patch(
        "/documents/507f1f77bcf86cd799439011",
        json={"estado": "desconocido"},
    )

    assert response.status_code == 422
    _clear_overrides()


def test_delete_document_returns_deleted_status() -> None:
    service = MagicMock()
    service.delete_document.return_value = True
    _override_service(service)

    response = client.delete("/documents/507f1f77bcf86cd799439011")

    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}
    _clear_overrides()


def test_delete_document_returns_404_when_missing() -> None:
    service = MagicMock()
    service.delete_document.return_value = False
    _override_service(service)

    response = client.delete("/documents/507f1f77bcf86cd799439011")

    assert response.status_code == 404
    assert response.json() == {"detail": "Documento no encontrado."}
    _clear_overrides()


def test_delete_document_rejects_invalid_id() -> None:
    service = MagicMock()
    _override_service(service)

    response = client.delete("/documents/id-invalido")

    assert response.status_code == 400
    assert response.json() == {"detail": main_module.INVALID_DOCUMENT_ID_ERROR_DETAIL}
    _clear_overrides()
