from dataclasses import replace
from unittest.mock import MagicMock

from bson.objectid import ObjectId
from fastapi.testclient import TestClient
import fitz

from app import main as main_module
from app.dependencies import get_document_service
from app.services import pdf_service as pdf_service_module
from app.services.document_service import DocumentService


def _override_service(service: DocumentService):
    main_module.app.dependency_overrides[get_document_service] = lambda: service


def _clear_overrides():
    main_module.app.dependency_overrides.clear()


client = TestClient(main_module.app)


def _build_valid_pdf_bytes() -> bytes:
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    return doc.write()


def test_upload_pdf_accepts_real_file(monkeypatch) -> None:
    pdf_bytes = _build_valid_pdf_bytes()
    files = {"file": ("documento.pdf", pdf_bytes, "application/pdf")}
    
    service = MagicMock(spec=DocumentService)
    service.repository = MagicMock()
    process_mock = MagicMock(
        return_value={
            "document_id": "507f1f77bcf86cd799439011",
            "document": {
                "txt_contenido": "",
            },
        }
    )
    monkeypatch.setattr("app.main.process_pdf_upload", process_mock)
    _override_service(service)

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "documento.pdf"
    assert payload["content_type"] == "application/pdf"
    assert payload["size_bytes"] == len(pdf_bytes)
    assert payload["status"] == "uploaded"
    assert payload["extracted_text"] == ""
    _clear_overrides()


def test_upload_pdf_delegates_processing_to_pdf_service(monkeypatch) -> None:
    pdf_bytes = _build_valid_pdf_bytes()
    files = {"file": ("documento.pdf", pdf_bytes, "application/pdf")}
    
    service = MagicMock(spec=DocumentService)
    service.repository = MagicMock()
    process_mock = MagicMock(
        return_value={
            "document_id": "507f1f77bcf86cd799439011",
            "document": {
                "txt_contenido": "texto desde service",
            },
        }
    )
    monkeypatch.setattr("app.main.process_pdf_upload", process_mock)
    _override_service(service)

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 200
    process_mock.assert_called_once_with(
        file_name="documento.pdf",
        file_bytes=pdf_bytes,
        repository=service.repository,
    )
    assert response.json()["extracted_text"] == "texto desde service"
    _clear_overrides()


def test_upload_pdf_rejects_non_pdf_file() -> None:
    service = MagicMock(spec=DocumentService)
    _override_service(service)
    
    files = {"file": ("texto.txt", b"hola", "text/plain")}

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": main_module.INVALID_CONTENT_TYPE_ERROR_DETAIL}
    _clear_overrides()


def test_upload_pdf_rejects_invalid_pdf_content(monkeypatch) -> None:
    service = MagicMock(spec=DocumentService)
    service.repository = MagicMock()
    process_mock = MagicMock(
        side_effect=pdf_service_module.InvalidPDFError(pdf_service_module.INVALID_PDF_CONTENT_ERROR)
    )
    monkeypatch.setattr("app.main.process_pdf_upload", process_mock)
    _override_service(service)

    files = {"file": ("falso.pdf", b"esto no es un pdf", "application/pdf")}

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": pdf_service_module.INVALID_PDF_CONTENT_ERROR}
    _clear_overrides()


def test_upload_pdf_rejects_file_over_max_size(monkeypatch) -> None:
    service = MagicMock(spec=DocumentService)
    _override_service(service)
    
    limited_settings = replace(main_module.settings, max_pdf_size_bytes=10)
    monkeypatch.setattr(main_module, "settings", limited_settings)

    files = {"file": ("documento.pdf", _build_valid_pdf_bytes(), "application/pdf")}
    response = client.post("/documents/upload", files=files)

    assert response.status_code == 413
    assert response.json() == {"detail": main_module.MAX_FILE_SIZE_ERROR_TEMPLATE.format(max_size=10)}
    _clear_overrides()


def test_download_document_returns_txt_attachment() -> None:
    document_id = ObjectId("507f1f77bcf86cd799439011")
    service = MagicMock(spec=DocumentService)
    service.get_document_by_id.return_value = {
        "_id": document_id,
        "pdf_nombre": "documento.pdf",
        "txt_contenido": "texto descargable",
    }
    _override_service(service)

    response = client.get(f"/documents/{document_id}/download")

    assert response.status_code == 200
    assert response.text == "texto descargable"
    assert response.headers["content-disposition"] == 'attachment; filename="documento.pdf.txt"'
    assert response.headers["content-type"].startswith("text/plain")
    _clear_overrides()


def test_download_document_returns_404_for_missing_document() -> None:
    service = MagicMock(spec=DocumentService)
    service.get_document_by_id.return_value = None
    _override_service(service)

    response = client.get("/documents/507f1f77bcf86cd799439011/download")

    assert response.status_code == 404
    assert response.json() == {"detail": "Documento no encontrado."}
    _clear_overrides()


def test_get_document_by_checksum_returns_document() -> None:
    service = MagicMock(spec=DocumentService)
    service.get_document_by_checksum.return_value = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "pdf_nombre": "documento.pdf",
        "txt_contenido": "texto existente",
    }
    _override_service(service)

    response = client.get("/documents/by-checksum/checksum123")

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == "507f1f77bcf86cd799439011"
    assert body["document"]["_id"] == "507f1f77bcf86cd799439011"
    assert body["document"]["txt_contenido"] == "texto existente"
    _clear_overrides()


def test_get_document_by_checksum_returns_404_when_missing() -> None:
    service = MagicMock(spec=DocumentService)
    service.get_document_by_checksum.return_value = None
    _override_service(service)

    response = client.get("/documents/by-checksum/checksum123")

    assert response.status_code == 404
    assert response.json() == {"detail": "Documento no encontrado."}
    _clear_overrides()


def test_upload_pdf_rejects_empty_file():
    service = MagicMock(spec=DocumentService)
    _override_service(service)
    
    files = {"file": ("vacio.pdf", b"", "application/pdf")}

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": main_module.EMPTY_FILE_ERROR_DETAIL}
    _clear_overrides()


def test_download_document_rejects_invalid_object_id():
    service = MagicMock(spec=DocumentService)
    _override_service(service)
    
    response = client.get("/documents/id-completamente-invalido/download")

    assert response.status_code == 400
    assert response.json() == {"detail": "ID de documento inválido."}
    _clear_overrides()
