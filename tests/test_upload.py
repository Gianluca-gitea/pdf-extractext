from dataclasses import replace
from io import BytesIO
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
import fitz

from app import main as main_module
from app.services import pdf_service as pdf_service_module


client = TestClient(main_module.app)


def _build_valid_pdf_bytes() -> bytes:
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    return doc.write()


def test_upload_pdf_accepts_real_file(monkeypatch) -> None:
    pdf_bytes = _build_valid_pdf_bytes()
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


def test_upload_pdf_delegates_processing_to_pdf_service(monkeypatch) -> None:
    pdf_bytes = _build_valid_pdf_bytes()
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
    )
    assert response.json()["extracted_text"] == "texto desde service"


def test_upload_pdf_rejects_non_pdf_file() -> None:
    files = {"file": ("texto.txt", b"hola", "text/plain")}

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": main_module.INVALID_CONTENT_TYPE_ERROR_DETAIL}


def test_upload_pdf_rejects_invalid_pdf_content() -> None:
    files = {"file": ("falso.pdf", b"esto no es un pdf", "application/pdf")}

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": pdf_service_module.INVALID_PDF_CONTENT_ERROR}


def test_upload_pdf_rejects_file_over_max_size(monkeypatch) -> None:
    limited_settings = replace(main_module.settings, max_pdf_size_bytes=10)
    monkeypatch.setattr(main_module, "settings", limited_settings)

    files = {"file": ("documento.pdf", _build_valid_pdf_bytes(), "application/pdf")}
    response = client.post("/documents/upload", files=files)

    assert response.status_code == 413
    assert response.json() == {"detail": main_module.MAX_FILE_SIZE_ERROR_TEMPLATE.format(max_size=10)}
