from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from tempfile import SpooledTemporaryFile
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.services import pdf_service as pdf_service_module

client = TestClient(main_module.app)


@pytest.fixture
def thread_pool(monkeypatch):
    with ThreadPoolExecutor(max_workers=1) as pool:
        monkeypatch.setattr(main_module, "get_extraction_pool", lambda: pool)
        yield pool


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


def test_extract_forwards_ocr_setting(monkeypatch, pdf_bytes, thread_pool) -> None:
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, ocr_enabled=True))
    extractor = MagicMock(return_value={"content": "x", "page_count": 1})
    monkeypatch.setattr(main_module, "extract_markdown_from_pdf_bytes", extractor)

    client.post("/extract", content=pdf_bytes, headers={"Content-Type": "application/pdf"})

    extractor.assert_called_once_with(pdf_bytes, ocr_enabled=True)


def test_get_extraction_pool_creates_one_thread_pool_from_settings(monkeypatch) -> None:
    pool_class = MagicMock()
    monkeypatch.setattr(main_module, "ThreadPoolExecutor", pool_class)
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, extract_workers=3))
    main_module.get_extraction_pool.cache_clear()

    try:
        first = main_module.get_extraction_pool()
        second = main_module.get_extraction_pool()
    finally:
        main_module.get_extraction_pool.cache_clear()

    assert first is second
    pool_class.assert_called_once_with(max_workers=3)


def test_extract_runs_extraction_in_the_extraction_pool(monkeypatch, pdf_bytes, thread_pool) -> None:
    submitted = MagicMock(wraps=thread_pool.submit)
    monkeypatch.setattr(thread_pool, "submit", submitted)

    response = client.post("/extract", content=pdf_bytes, headers={"Content-Type": "application/pdf"})

    assert response.status_code == 200
    submitted.assert_called_once_with(
        main_module.extract_markdown_from_pdf_bytes, pdf_bytes, ocr_enabled=False
    )


def test_extract_rejects_with_503_when_pending_limit_is_reached(monkeypatch, pdf_bytes) -> None:
    monkeypatch.setattr(main_module, "_pending_extractions", main_module.settings.max_pending_extractions)
    extractor = MagicMock()
    monkeypatch.setattr(main_module, "extract_markdown_from_pdf_bytes", extractor)

    response = client.post("/extract", content=pdf_bytes, headers={"Content-Type": "application/pdf"})

    assert response.status_code == 503
    assert response.headers["retry-after"] == "1"
    assert response.json() == {"detail": main_module.SERVICE_BUSY_ERROR_DETAIL}
    extractor.assert_not_called()


def test_extract_releases_pending_slot_after_success_and_failure(pdf_bytes, thread_pool) -> None:
    client.post("/extract", content=pdf_bytes, headers={"Content-Type": "application/pdf"})
    client.post("/extract", content=b"no es pdf", headers={"Content-Type": "application/pdf"})

    assert main_module._pending_extractions == 0


def test_extract_works_with_the_real_extraction_pool(pdf_bytes) -> None:
    response = client.post("/extract", content=pdf_bytes, headers={"Content-Type": "application/pdf"})

    assert response.status_code == 200
    assert response.json() == {"content": "Hola extract", "page_count": 1}
    
def test_extract_keeps_large_multipart_file_in_memory(monkeypatch) -> None:
    rollovers = []
    monkeypatch.setattr(SpooledTemporaryFile, "rollover", lambda self: rollovers.append(self))
    monkeypatch.setattr(
        main_module,
        "extract_markdown_from_pdf_bytes",
        lambda file_bytes, ocr_enabled: {"content": "", "page_count": 1},
    )
    large_pdf = b"%PDF-1.4" + b"0" * (2 * 1024 * 1024)

    response = client.post("/extract", files={"file": ("grande.pdf", large_pdf, "application/pdf")})

    assert response.status_code == 200
    assert rollovers == []

