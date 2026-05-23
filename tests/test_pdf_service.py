from unittest.mock import MagicMock

from bson.objectid import ObjectId

from app.services import pdf_service


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
