from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from bson.objectid import ObjectId
from pymongo.errors import DuplicateKeyError

from app.services import upload_service
from app.services.extract_client import InvalidPDFError
from app.models import DocumentBuilt, ExtractionResult, ProcessedUploadResult


def _make_builtin_document(**overrides) -> DocumentBuilt:
    data = {
        "pdf_nombre": "documento.pdf",
        "txt_contenido": "texto extraido",
        "txt_chars": len("texto extraido"),
        "checksum_archivo": "checksum123",
        "checksum_algoritmo": "sha256",
        "estado": "ok",
        "error": None,
        "created_at": datetime.now(timezone.utc),
        "deleted_at": None,
        "duracion_ms": 100,
    }
    data.update(overrides)
    return DocumentBuilt(**data)


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

    def fake_builder(**kwargs) -> DocumentBuilt:
        captured_builder_args.update(kwargs)
        return _make_builtin_document(
            pdf_nombre=kwargs["pdf_nombre"],
            txt_contenido=kwargs["texto_extraido"],
            checksum_archivo=kwargs["checksum_archivo"],
            duracion_ms=kwargs["duracion_ms"],
        )

    monkeypatch.setattr(upload_service, "construir_documento", fake_builder)

    result = upload_service.process_pdf_upload(
        file_name=file_name,
        file_bytes=file_bytes,
        repository=repository,
        extractor=lambda received_bytes: ExtractionResult(
            content="texto extraido", page_count=1
        ),
    )

    assert isinstance(result, ProcessedUploadResult)
    assert captured_builder_args["pdf_nombre"] == file_name
    assert captured_builder_args["texto_extraido"] == "texto extraido"
    assert captured_builder_args["checksum_archivo"] == "checksum123"
    assert isinstance(captured_builder_args["duracion_ms"], int)
    repository.save_document.assert_called_once_with(result.document)
    assert result.document.txt_contenido == "texto extraido"
    assert result.document_id == "507f1f77bcf86cd799439011"


def test_process_pdf_upload_returns_existing_document_if_checksum_is_found(
    monkeypatch,
) -> None:
    repository = MagicMock()
    repository.find_by_checksum.return_value = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "pdf_nombre": "documento.pdf",
        "txt_contenido": "texto ya procesado",
        "txt_chars": 20,
        "checksum_archivo": "checksum123",
        "checksum_algoritmo": "sha256",
        "estado": "ok",
        "error": None,
        "created_at": datetime.now(timezone.utc),
        "deleted_at": None,
        "duracion_ms": 50,
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
    assert isinstance(result, ProcessedUploadResult)
    assert result.document_id == "507f1f77bcf86cd799439011"
    assert result.document.txt_contenido == "texto ya procesado"


def test_process_pdf_upload_sends_file_bytes_to_extractor() -> None:
    repository = MagicMock()
    repository.find_by_checksum.return_value = None
    extractor = MagicMock(return_value=ExtractionResult(content="texto", page_count=1))

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
    extract_text = MagicMock(
        return_value=ExtractionResult(content="texto remoto", page_count=1)
    )
    monkeypatch.setattr(upload_service, "extract_text", extract_text)

    result = upload_service.process_pdf_upload(
        file_name="a.pdf", file_bytes=b"%PDF-1.4", repository=repository
    )

    extract_text.assert_called_once_with(b"%PDF-1.4")
    assert isinstance(result, ProcessedUploadResult)
    assert result.document.txt_contenido == "texto remoto"


def test_process_pdf_upload_does_not_save_when_extraction_fails() -> None:
    repository = MagicMock()
    repository.find_by_checksum.return_value = None

    def invalid_pdf(file_bytes):
        raise InvalidPDFError("no es un pdf")

    with pytest.raises(InvalidPDFError):
        upload_service.process_pdf_upload(
            file_name="a.pdf",
            file_bytes=b"basura",
            repository=repository,
            extractor=invalid_pdf,
        )

    repository.save_document.assert_not_called()


def test_process_pdf_upload_uses_shared_repository_by_default(monkeypatch) -> None:
    shared_repository = MagicMock()
    shared_repository.find_by_checksum.return_value = {
        "_id": "id",
        "txt_contenido": "texto",
        "pdf_nombre": "a.pdf",
        "txt_chars": 5,
        "checksum_archivo": "abc",
        "checksum_algoritmo": "sha256",
        "estado": "ok",
        "error": None,
        "created_at": datetime.now(timezone.utc),
        "deleted_at": None,
        "duracion_ms": 0,
    }
    monkeypatch.setattr(upload_service, "get_document_repository", lambda: shared_repository)

    upload_service.process_pdf_upload(file_name="a.pdf", file_bytes=b"%PDF-1.4")

    shared_repository.find_by_checksum.assert_called_once()


def test_process_pdf_upload_returns_winner_of_concurrent_duplicate_upload() -> None:
    winner_model = _make_builtin_document(txt_contenido="texto")
    repository = MagicMock()
    repository.find_by_checksum.side_effect = [
        None,
        {"_id": "id-ganador", **winner_model.model_dump()},
    ]
    repository.save_document.side_effect = DuplicateKeyError("checksum duplicado")

    result = upload_service.process_pdf_upload(
        file_name="a.pdf",
        file_bytes=b"%PDF-1.4",
        repository=repository,
        extractor=lambda _: ExtractionResult(content="texto", page_count=1),
    )

    assert isinstance(result, ProcessedUploadResult)
    assert result.document_id == "id-ganador"
    assert result.document.txt_contenido == "texto"


def test_process_pdf_upload_reraises_duplicate_when_winner_is_gone() -> None:
    repository = MagicMock()
    repository.find_by_checksum.return_value = None
    repository.save_document.side_effect = DuplicateKeyError("checksum duplicado")

    with pytest.raises(DuplicateKeyError):
        upload_service.process_pdf_upload(
            file_name="a.pdf",
            file_bytes=b"%PDF-1.4",
            repository=repository,
            extractor=lambda _: ExtractionResult(content="texto", page_count=1),
        )
