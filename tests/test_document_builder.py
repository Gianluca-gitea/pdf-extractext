from datetime import datetime

from app.services.document_builder import construir_documento


class TestDocumentBuilder:
    """Tests for document construction."""

    def _build_document(self, **overrides) -> dict:
        data = {
            "pdf_nombre": "test.pdf",
            "texto_extraido": "test content",
            "checksum_archivo": "abc123",
            "duracion_ms": 100,
        }
        data.update(overrides)

        return construir_documento(**data)

    def test_construir_documento_returns_dict(self) -> None:
        result = self._build_document()

        assert isinstance(result, dict)

    def test_construir_documento_has_required_fields(self) -> None:
        result = self._build_document()

        expected_fields = {
            "pdf_nombre",
            "txt_contenido",
            "txt_chars",
            "checksum_archivo",
            "checksum_algoritmo",
            "estado",
            "error",
            "created_at",
            "deleted_at",
            "duracion_ms",
        }

        assert set(result.keys()) == expected_fields

    def test_construir_documento_preserves_pdf_nombre(self) -> None:
        pdf_nombre = "documento.pdf"

        result = self._build_document(pdf_nombre=pdf_nombre)

        assert result["pdf_nombre"] == pdf_nombre

    def test_construir_documento_preserves_texto_extraido(self) -> None:
        texto_extraido = "This is extracted text from PDF"

        result = self._build_document(texto_extraido=texto_extraido)

        assert result["txt_contenido"] == texto_extraido

    def test_construir_documento_calculates_txt_chars_correctly(self) -> None:
        texto_extraido = "Hello World"

        result = self._build_document(texto_extraido=texto_extraido)

        assert result["txt_chars"] == len(texto_extraido)

    def test_construir_documento_txt_chars_for_empty_text(self) -> None:
        result = self._build_document(texto_extraido="")

        assert result["txt_chars"] == 0

    def test_construir_documento_preserves_checksum(self) -> None:
        checksum_archivo = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"

        result = self._build_document(checksum_archivo=checksum_archivo)

        assert result["checksum_archivo"] == checksum_archivo

    def test_construir_documento_uses_sha256_algorithm(self) -> None:
        result = self._build_document()

        assert result["checksum_algoritmo"] == "sha256"

    def test_construir_documento_default_estado_is_pendiente(self) -> None:
        result = self._build_document()

        assert result["estado"] == "pendiente"

    def test_construir_documento_custom_estado(self) -> None:
        result = self._build_document(estado="error")

        assert result["estado"] == "error"

    def test_construir_documento_default_error_is_none(self) -> None:
        result = self._build_document()

        assert result["error"] is None

    def test_construir_documento_custom_error(self) -> None:
        error_msg = "Invalid PDF format"

        result = self._build_document(
            texto_extraido="",
            estado="error",
            error=error_msg,
        )

        assert result["error"] == error_msg

    def test_construir_documento_created_at_is_datetime(self) -> None:
        result = self._build_document()

        assert isinstance(result["created_at"], datetime)

    def test_construir_documento_deleted_at_is_none(self) -> None:
        result = self._build_document()

        assert result["deleted_at"] is None

    def test_construir_documento_preserves_duracion_ms(self) -> None:
        duracion_ms = 1500

        result = self._build_document(duracion_ms=duracion_ms)

        assert result["duracion_ms"] == duracion_ms
