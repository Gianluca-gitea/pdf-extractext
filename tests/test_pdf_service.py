from unittest.mock import MagicMock

from bson.objectid import ObjectId

from app.services import pdf_service

import pytest
import fitz
from app.services.pdf_service import (
    extract_text_from_pdf_bytes,
    InvalidPDFError,
    _extract_text_from_image_bytes,
)


def test_process_pdf_upload_orchestrates_checksum_builder_and_repository(
    monkeypatch,
) -> None:
    file_name = "documento.pdf"
    file_bytes = b"%PDF-1.4 test"
    repository = MagicMock()
    repository.save_document.return_value = ObjectId("507f1f77bcf86cd799439011")
    repository.find_by_checksum.return_value = None

    monkeypatch.setattr(
        pdf_service,
        "extract_text_from_pdf_bytes",
        lambda received_bytes: "texto extraido",
    )
    monkeypatch.setattr(
        pdf_service,
        "calc_checksum",
        lambda received_bytes: "checksum123",
    )

    captured_builder_args = {}

    def fake_builder(**kwargs):
        captured_builder_args.update(kwargs)
        return {
            "pdf_nombre": kwargs["pdf_nombre"],
            "txt_contenido": kwargs["texto_extraido"],
            "txt_chars": len(kwargs["texto_extraido"]),
            "checksum_archivo": kwargs["checksum_archivo"],
            "checksum_algoritmo": "sha256",
            "estado": "ok",
            "error": None,
            "created_at": "now",
            "duracion_ms": kwargs["duracion_ms"],
        }

    monkeypatch.setattr(pdf_service, "construir_documento", fake_builder)

    result = pdf_service.process_pdf_upload(
        file_name=file_name,
        file_bytes=file_bytes,
        repository=repository,
    )

    assert captured_builder_args["pdf_nombre"] == file_name
    assert captured_builder_args["texto_extraido"] == "texto extraido"
    assert captured_builder_args["checksum_archivo"] == "checksum123"
    assert isinstance(captured_builder_args["duracion_ms"], int)
    repository.save_document.assert_called_once_with(result["document"])
    assert result["document"]["txt_contenido"] == "texto extraido"
    assert result["document_id"] == "507f1f77bcf86cd799439011"


def test_process_pdf_upload_returns_existing_document_if_checksum_is_found(
    monkeypatch,
) -> None:
    file_name = "documento.pdf"
    file_bytes = b"%PDF-1.4 test"
    repository = MagicMock()
    repository.find_by_checksum.return_value = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "txt_contenido": "texto ya procesado",
    }

    extract_text_mock = MagicMock()
    monkeypatch.setattr(pdf_service, "extract_text_from_pdf_bytes", extract_text_mock)
    monkeypatch.setattr(pdf_service, "calc_checksum", lambda received_bytes: "checksum123")

    result = pdf_service.process_pdf_upload(
        file_name=file_name,
        file_bytes=file_bytes,
        repository=repository,
    )

    extract_text_mock.assert_not_called()
    repository.save_document.assert_not_called()
    assert result["document_id"] == "507f1f77bcf86cd799439011"
    assert result["document"]["txt_contenido"] == "texto ya procesado"


def test_extract_text_from_pdf_bytes_raises_error_if_not_pdf():
    with pytest.raises(InvalidPDFError, match="El contenido no corresponde a un PDF valido."):
        extract_text_from_pdf_bytes(b"esto no es un pdf, son bytes al azar")


def test_extract_text_from_pdf_bytes_extracts_real_text():
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((10, 10), "Hola mundo real")
    pdf_bytes = doc.write()

    result = extract_text_from_pdf_bytes(pdf_bytes)
    assert "Hola mundo real" in result


def test_extract_text_from_image_bytes_returns_empty_on_none():
    result = _extract_text_from_image_bytes(None)
    assert result == ""


def test_extract_text_from_pdf_bytes_handles_fitz_open_error(monkeypatch):
    def mock_open(*args, **kwargs):
        raise ValueError("Error interno de PyMuPDF")

    monkeypatch.setattr("fitz.open", mock_open)

    with pytest.raises(InvalidPDFError, match="El contenido no corresponde a un PDF valido."):
        extract_text_from_pdf_bytes(b"%PDF-1.4 pero corrupto")


def test_extract_text_from_image_bytes_uses_ocr_successfully(mocker):
    mock_image_open = mocker.patch("PIL.Image.open")
    mock_pytesseract = mocker.patch("pytesseract.image_to_string", return_value="texto detectado en imagen\n")

    result = _extract_text_from_image_bytes(b"fake image bytes")

    mock_image_open.assert_called_once()
    mock_pytesseract.assert_called_once()
    assert result == "texto detectado en imagen"
