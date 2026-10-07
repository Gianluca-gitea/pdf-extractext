import asyncio
from dataclasses import replace
from tempfile import SpooledTemporaryFile
from unittest.mock import MagicMock

import pytest
from bson.objectid import ObjectId
from fastapi.testclient import TestClient

from app import main as main_module
from app.services import pdf_service as pdf_service_module

client = TestClient(main_module.app)


def test_upload_pdf_accepts_real_file(monkeypatch, pdf_bytes) -> None:
    files = {"file": ("documento.pdf", pdf_bytes, "application/pdf")}
    process_mock = MagicMock(
        return_value={
            "document_id": "507f1f77bcf86cd799439011",
            "document": {
                "txt_contenido": "",
            },
        }
    )
    monkeypatch.setattr(main_module, "process_pdf_upload", process_mock)

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "documento.pdf"
    assert payload["content_type"] == "application/pdf"
    assert payload["size_bytes"] == len(pdf_bytes)
    assert payload["status"] == "uploaded"
    assert payload["extracted_text"] == ""


def test_upload_pdf_delegates_processing_to_pdf_service(monkeypatch, pdf_bytes) -> None:
    files = {"file": ("documento.pdf", pdf_bytes, "application/pdf")}
    process_mock = MagicMock(
        return_value={
            "document_id": "507f1f77bcf86cd799439011",
            "document": {
                "txt_contenido": "texto desde service",
            },
        }
    )
    monkeypatch.setattr(main_module, "process_pdf_upload", process_mock)

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 200
    process_mock.assert_called_once_with(
        file_name="documento.pdf",
        file_bytes=pdf_bytes,
        ocr_enabled=main_module.settings.ocr_enabled,
    )
    assert response.json()["extracted_text"] == "texto desde service"


def test_upload_pdf_rejects_non_pdf_file() -> None:
    files = {"file": ("texto.txt", b"hola", "text/plain")}

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": main_module.INVALID_CONTENT_TYPE_ERROR_DETAIL}


def test_upload_pdf_rejects_invalid_pdf_content(monkeypatch) -> None:
    process_mock = MagicMock()
    process_mock.find_by_checksum.return_value = None
    monkeypatch.setattr(pdf_service_module, "get_document_repository", lambda: process_mock)

    files = {"file": ("falso.pdf", b"esto no es un pdf", "application/pdf")}

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": pdf_service_module.INVALID_PDF_CONTENT_ERROR}


def test_upload_pdf_rejects_file_over_max_size(monkeypatch, pdf_bytes) -> None:
    limited_settings = replace(main_module.settings, max_pdf_size_bytes=10)
    monkeypatch.setattr(main_module, "settings", limited_settings)

    files = {"file": ("documento.pdf", pdf_bytes, "application/pdf")}
    response = client.post("/documents/upload", files=files)

    assert response.status_code == 413
    assert response.json() == {"detail": main_module.MAX_FILE_SIZE_ERROR_TEMPLATE.format(max_size=10)}


def test_download_document_returns_txt_attachment(monkeypatch) -> None:
    document_id = ObjectId("507f1f77bcf86cd799439011")
    service = MagicMock()
    service.get_document_by_id.return_value = {
        "_id": document_id,
        "pdf_nombre": "documento.pdf",
        "txt_contenido": "texto descargable",
    }

    monkeypatch.setattr(main_module, "DocumentService", lambda: service)

    response = client.get(f"/documents/{document_id}/download")

    assert response.status_code == 200
    assert response.text == "texto descargable"
    assert response.headers["content-disposition"] == 'attachment; filename="documento.pdf.txt"'
    assert response.headers["content-type"].startswith("text/plain")


def test_download_document_returns_404_for_missing_document(monkeypatch) -> None:
    service = MagicMock()
    service.get_document_by_id.return_value = None
    monkeypatch.setattr(main_module, "DocumentService", lambda: service)

    response = client.get("/documents/507f1f77bcf86cd799439011/download")

    assert response.status_code == 404
    assert response.json() == {"detail": "Documento no encontrado."}


def test_get_document_by_checksum_returns_document(monkeypatch) -> None:
    service = MagicMock()
    service.get_document_by_checksum.return_value = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "pdf_nombre": "documento.pdf",
        "txt_contenido": "texto existente",
    }
    monkeypatch.setattr(main_module, "DocumentService", lambda: service)

    response = client.get("/documents/by-checksum/checksum123")

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == "507f1f77bcf86cd799439011"
    assert body["document"]["_id"] == "507f1f77bcf86cd799439011"
    assert body["document"]["txt_contenido"] == "texto existente"


def test_get_document_by_checksum_returns_404_when_missing(monkeypatch) -> None:
    service = MagicMock()
    service.get_document_by_checksum.return_value = None
    monkeypatch.setattr(main_module, "DocumentService", lambda: service)

    response = client.get("/documents/by-checksum/checksum123")

    assert response.status_code == 404
    assert response.json() == {"detail": "Documento no encontrado."}


def test_upload_pdf_rejects_empty_file():
    files = {"file": ("vacio.pdf", b"", "application/pdf")}

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": main_module.EMPTY_FILE_ERROR_DETAIL}


def test_download_document_rejects_invalid_object_id():
    response = client.get("/documents/id-completamente-invalido/download")

    assert response.status_code == 400
    assert response.json() == {"detail": "ID de documento inválido."}


def test_upload_pdf_processes_outside_the_event_loop(monkeypatch, pdf_bytes) -> None:
    def process_off_loop(**kwargs):
        with pytest.raises(RuntimeError):
            asyncio.get_running_loop()
        return {"document_id": "id", "document": {"txt_contenido": ""}}

    monkeypatch.setattr(main_module, "process_pdf_upload", process_off_loop)
    files = {"file": ("documento.pdf", pdf_bytes, "application/pdf")}

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 200
    
def test_upload_pdf_keeps_large_file_in_memory(monkeypatch) -> None:
    rollovers = []
    monkeypatch.setattr(SpooledTemporaryFile, "rollover", lambda self: rollovers.append(self))
    monkeypatch.setattr(
        main_module,
        "process_pdf_upload",
        MagicMock(return_value={"document_id": "id", "document": {"txt_contenido": ""}}),
    )
    large_pdf = b"%PDF-1.4" + b"0" * (2 * 1024 * 1024)  # 2 MB PDF content
    
    response = client.post("/documents/upload", files={"file": ("grande.pdf", large_pdf, "application/pdf")})

    assert response.status_code == 200
    assert rollovers == []
