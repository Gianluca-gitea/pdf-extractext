import asyncio
from dataclasses import replace
from tempfile import SpooledTemporaryFile
from unittest.mock import MagicMock

import pytest
from bson.objectid import ObjectId
from fastapi.testclient import TestClient

from app import main as main_module
from app.services import extract_client as extract_client_module
from app.services import upload_service as upload_service_module

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


def test_upload_pdf_delegates_processing_to_upload_service(monkeypatch, pdf_bytes) -> None:
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


@pytest.fixture
def empty_repository(monkeypatch) -> MagicMock:
    repository = MagicMock()
    repository.find_by_checksum.return_value = None
    monkeypatch.setattr(upload_service_module, "get_document_repository", lambda: repository)
    return repository


def _extract_text_raising(monkeypatch, error: Exception) -> None:
    def failing_extract(file_bytes):
        raise error

    monkeypatch.setattr(upload_service_module, "extract_text", failing_extract)


def test_upload_pdf_rejects_invalid_pdf_content(monkeypatch, empty_repository) -> None:
    detail = "El contenido no corresponde a un PDF valido."
    _extract_text_raising(monkeypatch, extract_client_module.InvalidPDFError(detail))

    files = {"file": ("falso.pdf", b"esto no es un pdf", "application/pdf")}

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": detail}
    empty_repository.save_document.assert_not_called()


def test_upload_pdf_returns_503_when_extract_service_is_busy(
    monkeypatch, empty_repository, pdf_bytes
) -> None:
    _extract_text_raising(monkeypatch, extract_client_module.ExtractServiceBusyError("2"))

    response = client.post(
        "/documents/upload", files={"file": ("a.pdf", pdf_bytes, "application/pdf")}
    )

    assert response.status_code == 503
    assert response.headers["retry-after"] == "2"
    assert response.json() == {"detail": main_module.SERVICE_BUSY_ERROR_DETAIL}
    empty_repository.save_document.assert_not_called()


def test_upload_pdf_returns_504_when_extract_service_times_out(
    monkeypatch, empty_repository, pdf_bytes
) -> None:
    _extract_text_raising(monkeypatch, extract_client_module.ExtractServiceTimeoutError("lento"))

    response = client.post(
        "/documents/upload", files={"file": ("a.pdf", pdf_bytes, "application/pdf")}
    )

    assert response.status_code == 504
    assert response.json() == {"detail": "lento"}


def test_upload_pdf_returns_502_when_extract_service_is_down(
    monkeypatch, empty_repository, pdf_bytes
) -> None:
    _extract_text_raising(
        monkeypatch, extract_client_module.ExtractServiceUnavailableError("caído")
    )

    response = client.post(
        "/documents/upload", files={"file": ("a.pdf", pdf_bytes, "application/pdf")}
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "caído"}
    empty_repository.save_document.assert_not_called()


def test_upload_pdf_does_not_call_extract_service_for_duplicates(monkeypatch, pdf_bytes) -> None:
    repository = MagicMock()
    repository.find_by_checksum.return_value = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "txt_contenido": "ya estaba",
    }
    monkeypatch.setattr(upload_service_module, "get_document_repository", lambda: repository)
    _extract_text_raising(monkeypatch, AssertionError("no deberia llamar a extract"))

    response = client.post(
        "/documents/upload", files={"file": ("a.pdf", pdf_bytes, "application/pdf")}
    )

    assert response.status_code == 200
    assert response.json()["extracted_text"] == "ya estaba"


def test_upload_pdf_rejects_file_over_max_size(monkeypatch, pdf_bytes) -> None:
    limited_settings = replace(main_module.settings, max_pdf_size_bytes=10)
    monkeypatch.setattr(main_module, "settings", limited_settings)

    files = {"file": ("documento.pdf", pdf_bytes, "application/pdf")}
    response = client.post("/documents/upload", files=files)

    assert response.status_code == 413
    assert response.json() == {
        "detail": main_module.MAX_FILE_SIZE_ERROR_TEMPLATE.format(max_size=10)
    }


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

    response = client.post(
        "/documents/upload", files={"file": ("grande.pdf", large_pdf, "application/pdf")}
    )

    assert response.status_code == 200
    assert rollovers == []


def test_shutdown_closes_extract_client_and_mongo_client(monkeypatch) -> None:
    close_extract = MagicMock()
    close_repository = MagicMock()
    monkeypatch.setattr(main_module, "close_extract_client", close_extract)
    monkeypatch.setattr(main_module, "close_document_repository", close_repository)

    with TestClient(main_module.app):
        pass

    close_extract.assert_called_once_with()
    close_repository.assert_called_once_with()
