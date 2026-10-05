from dataclasses import replace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app import main as main_module
from app.services import pdf_service as pdf_service_module

client = TestClient(main_module.app)


def test_extract_accepts_multipart_file(pdf_bytes) -> None:
    files = {"file": ("documento.pdf", pdf_bytes, "application/pdf")}

    response = client.post("/extract", files=files)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"content": "Hola extract", "page_count": 1}


def test_extract_accepts_raw_binary_body(pdf_bytes) -> None:
    response = client.post(
        "/extract",
        content=pdf_bytes,
        headers={"Content-Type": "application/pdf"},
    )

    assert response.status_code == 200
    assert response.json() == {"content": "Hola extract", "page_count": 1}


def test_extract_rejects_multipart_without_file_field() -> None:
    response = client.post("/extract", files={"otro": ("a.pdf", b"%PDF-", "application/pdf")})

    assert response.status_code == 400
    assert response.json() == {"detail": main_module.MISSING_FILE_FIELD_ERROR_DETAIL}


def test_extract_rejects_empty_body() -> None:
    response = client.post("/extract", content=b"", headers={"Content-Type": "application/pdf"})

    assert response.status_code == 400
    assert response.json() == {"detail": main_module.EMPTY_FILE_ERROR_DETAIL}


def test_extract_rejects_file_over_max_size(monkeypatch, pdf_bytes) -> None:
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, max_pdf_size_bytes=10))

    response = client.post(
        "/extract",
        content=pdf_bytes,
        headers={"Content-Type": "application/pdf"},
    )

    assert response.status_code == 413
    assert response.json() == {
        "detail": main_module.MAX_FILE_SIZE_ERROR_TEMPLATE.format(max_size=10)
    }


def test_extract_rejects_invalid_pdf_content() -> None:
    response = client.post(
        "/extract",
        content=b"esto no es un pdf",
        headers={"Content-Type": "application/pdf"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": pdf_service_module.INVALID_PDF_CONTENT_ERROR}


def test_extract_does_not_touch_the_database(monkeypatch, pdf_bytes) -> None:
    repository = MagicMock()
    document_service = MagicMock()
    monkeypatch.setattr(pdf_service_module, "get_document_repository", repository)
    monkeypatch.setattr(main_module, "DocumentService", document_service)

    response = client.post(
        "/extract",
        content=pdf_bytes,
        headers={"Content-Type": "application/pdf"},
    )

    assert response.status_code == 200
    repository.assert_not_called()
    document_service.assert_not_called()


def test_extract_forwards_ocr_setting(monkeypatch, pdf_bytes) -> None:
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, ocr_enabled=True))
    extractor = MagicMock(return_value={"content": "x", "page_count": 1})
    monkeypatch.setattr(main_module, "extract_markdown_from_pdf_bytes", extractor)

    client.post("/extract", content=pdf_bytes, headers={"Content-Type": "application/pdf"})

    extractor.assert_called_once_with(pdf_bytes, ocr_enabled=True)
