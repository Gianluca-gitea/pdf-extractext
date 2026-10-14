from unittest.mock import MagicMock

import pytest
from bson.objectid import ObjectId
from pymongo.errors import DuplicateKeyError

from app.services import upload_service
from app.services.extract_client import InvalidPDFError


def test_process_pdf_upload_orchestrates_checksum_builder_and_repository(
    monkeypatch,
) -> None:
    file_name = "documento.pdf"
    file_bytes = b"%PDF-1.4 test"
    repository = MagicMock()
    repository.save_document.return_value = ObjectId("507f1f77bcf86cd799439011")
    repository.find_by_checksum.return_value = None

    monkeypatch.setattr(
        upload_service,
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

    monkeypatch.setattr(upload_service, "construir_documento", fake_builder)

    result = upload_service.process_pdf_upload(
        file_name=file_name,
        file_bytes=file_bytes,
        repository=repository,
        extractor=lambda received_bytes: "texto extraido",
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
    repository = MagicMock()
    repository.find_by_checksum.return_value = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "txt_contenido": "texto ya procesado",
    }
    extractor = MagicMock()
    monkeypatch.setattr(upload_service, "calc_checksum", lambda received_bytes: "checksum123")

    result = upload_service.process_pdf_upload(
        file_name="documento.pdf",
        file_bytes=b"%PDF-1.4 test",
        repository=repository,
        extractor=extractor,
    )

    extractor.assert_not_called()
    repository.save_document.assert_not_called()
    assert result["document_id"] == "507f1f77bcf86cd799439011"
    assert result["document"]["txt_contenido"] == "texto ya procesado"


def test_process_pdf_upload_sends_file_bytes_to_extractor() -> None:
    repository = MagicMock()
    repository.find_by_checksum.return_value = None
    extractor = MagicMock(return_value="texto")

    upload_service.process_pdf_upload(
        file_name="documento.pdf",
        file_bytes=b"%PDF-1.4 test",
        repository=repository,
        extractor=extractor,
    )

    extractor.assert_called_once_with(b"%PDF-1.4 test")


def test_process_pdf_upload_uses_extract_client_by_default(monkeypatch) -> None:
    repository = MagicMock()
    repository.find_by_checksum.return_value = None
    extract_text = MagicMock(return_value="texto remoto")
    monkeypatch.setattr(upload_service, "extract_text", extract_text)

    result = upload_service.process_pdf_upload(
        file_name="a.pdf", file_bytes=b"%PDF-1.4", repository=repository
    )

    extract_text.assert_called_once_with(b"%PDF-1.4")
    assert result["document"]["txt_contenido"] == "texto remoto"


def test_process_pdf_upload_does_not_save_when_extraction_fails() -> None:
    repository = MagicMock()
    repository.find_by_checksum.return_value = None

    def invalid_pdf(file_bytes):
        raise InvalidPDFError("no es un pdf")

    with pytest.raises(InvalidPDFError):
        upload_service.process_pdf_upload(
            file_name="a.pdf", file_bytes=b"basura", repository=repository, extractor=invalid_pdf
        )

    repository.save_document.assert_not_called()


def test_process_pdf_upload_uses_shared_repository_by_default(monkeypatch) -> None:
    shared_repository = MagicMock()
    shared_repository.find_by_checksum.return_value = {"_id": "id", "txt_contenido": "texto"}
    monkeypatch.setattr(upload_service, "get_document_repository", lambda: shared_repository)

    upload_service.process_pdf_upload(file_name="a.pdf", file_bytes=b"%PDF-1.4")

    shared_repository.find_by_checksum.assert_called_once()


def test_process_pdf_upload_returns_winner_of_concurrent_duplicate_upload() -> None:
    winner = {"_id": "id-ganador", "txt_contenido": "texto"}
    repository = MagicMock()
    repository.find_by_checksum.side_effect = [None, winner]
    repository.save_document.side_effect = DuplicateKeyError("checksum duplicado")

    result = upload_service.process_pdf_upload(
        file_name="a.pdf",
        file_bytes=b"%PDF-1.4",
        repository=repository,
        extractor=lambda _: "texto",
    )

    assert result == {"document_id": "id-ganador", "document": winner}


def test_process_pdf_upload_reraises_duplicate_when_winner_is_gone() -> None:
    repository = MagicMock()
    repository.find_by_checksum.return_value = None
    repository.save_document.side_effect = DuplicateKeyError("checksum duplicado")

    with pytest.raises(DuplicateKeyError):
        upload_service.process_pdf_upload(
            file_name="a.pdf",
            file_bytes=b"%PDF-1.4",
            repository=repository,
            extractor=lambda _: "texto",
        )
