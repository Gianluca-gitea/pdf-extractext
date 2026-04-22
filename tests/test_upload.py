from dataclasses import replace
from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app import main as main_module


client = TestClient(main_module.app)


def _build_valid_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_upload_pdf_accepts_real_file() -> None:
    pdf_bytes = _build_valid_pdf_bytes()
    files = {"file": ("documento.pdf", pdf_bytes, "application/pdf")}

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "documento.pdf"
    assert payload["content_type"] == "application/pdf"
    assert payload["size_bytes"] == len(pdf_bytes)
    assert payload["status"] == "uploaded"
    assert payload["extracted_text"] == ""


def test_upload_pdf_rejects_non_pdf_file() -> None:
    files = {"file": ("texto.txt", b"hola", "text/plain")}

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": "El archivo debe enviarse como application/pdf."}


def test_upload_pdf_rejects_invalid_pdf_content() -> None:
    files = {"file": ("falso.pdf", b"esto no es un pdf", "application/pdf")}

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": "El contenido no corresponde a un PDF valido."}


def test_upload_pdf_rejects_file_over_max_size(monkeypatch) -> None:
    limited_settings = replace(main_module.settings, max_pdf_size_bytes=10)
    monkeypatch.setattr(main_module, "settings", limited_settings)

    files = {"file": ("documento.pdf", _build_valid_pdf_bytes(), "application/pdf")}
    response = client.post("/documents/upload", files=files)

    assert response.status_code == 413
    assert response.json() == {"detail": "El archivo supera el tamano maximo permitido de 10 bytes."}
