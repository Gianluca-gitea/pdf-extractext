import fitz
import pytest

from app import pdf_service
from app.pdf_service import (
    extract_markdown_from_pdf_bytes,
    extract_text_from_pdf_bytes,
    INVALID_PDF_CONTENT_ERROR,
    InvalidPDFError,
    _extract_text_from_image_bytes,
)


def _fail_ocr(image_bytes):
    raise AssertionError("OCR no deberia ejecutarse")


def test_extract_text_from_pdf_bytes_raises_error_if_not_pdf():
    with pytest.raises(InvalidPDFError, match="El contenido no corresponde a un PDF valido."):
        extract_text_from_pdf_bytes(b"esto no es un pdf, son bytes al azar", ocr_enabled=False)


def test_extract_text_from_pdf_bytes_extracts_real_text():
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((10, 10), "Hola mundo real")
    pdf_bytes = doc.write()

    result = extract_text_from_pdf_bytes(pdf_bytes, ocr_enabled=False)
    assert "Hola mundo real" in result["content"]
    assert result["page_count"] == 1


def test_extract_text_from_image_bytes_returns_empty_on_none():
    result = _extract_text_from_image_bytes(None)
    assert result == ""


def test_extract_text_from_pdf_bytes_handles_fitz_open_error(monkeypatch):
    def mock_open(*args, **kwargs):
        raise ValueError("Error interno de PyMuPDF")

    monkeypatch.setattr("fitz.open", mock_open)

    with pytest.raises(InvalidPDFError, match="El contenido no corresponde a un PDF valido."):
        extract_text_from_pdf_bytes(b"%PDF-1.4 pero corrupto", ocr_enabled=False)


def test_extract_text_from_image_bytes_uses_ocr_successfully(mocker):
    mock_image_open = mocker.patch("PIL.Image.open")
    mock_pytesseract = mocker.patch(
        "pytesseract.image_to_string", return_value="texto detectado en imagen\n"
    )

    result = _extract_text_from_image_bytes(b"fake image bytes")

    mock_image_open.assert_called_once()
    mock_pytesseract.assert_called_once()
    assert result == "texto detectado en imagen"


def test_extract_text_from_pdf_bytes_skips_ocr_when_disabled(monkeypatch, pdf_with_image):
    monkeypatch.setattr(pdf_service, "_extract_text_from_image_bytes", _fail_ocr)

    result = extract_text_from_pdf_bytes(pdf_with_image, ocr_enabled=False)

    assert result["content"] == "Texto normal"


def test_extract_text_from_pdf_bytes_runs_ocr_when_enabled(monkeypatch, pdf_with_image):
    monkeypatch.setattr(pdf_service, "_extract_text_from_image_bytes", lambda _: "texto ocr")

    result = extract_text_from_pdf_bytes(pdf_with_image, ocr_enabled=True)

    assert result["content"] == "Texto normal\ntexto ocr"


def test_extract_markdown_rejects_non_pdf_bytes() -> None:
    with pytest.raises(InvalidPDFError, match=INVALID_PDF_CONTENT_ERROR):
        extract_markdown_from_pdf_bytes(b"esto no es un pdf", ocr_enabled=False)


def test_extract_markdown_counts_pages(build_pdf) -> None:
    pdf_bytes = build_pdf([("uno", 11)], [("dos", 11)], [("tres", 11)])

    result = extract_markdown_from_pdf_bytes(pdf_bytes, ocr_enabled=False)

    assert result["page_count"] == 3


def test_extract_markdown_returns_empty_content_for_blank_page(build_pdf) -> None:
    result = extract_markdown_from_pdf_bytes(build_pdf([]), ocr_enabled=False)

    assert result == {"content": "", "page_count": 1}


def test_extract_markdown_separates_blocks_as_paragraphs_across_pages(build_pdf) -> None:
    pdf_bytes = build_pdf([("Primer parrafo", 11), ("Segundo parrafo", 11)], [("Pagina dos", 11)])

    result = extract_markdown_from_pdf_bytes(pdf_bytes, ocr_enabled=False)

    assert result["content"] == "Primer parrafo\n\nSegundo parrafo\n\nPagina dos"


def test_extract_markdown_marks_large_text_as_headings(build_pdf) -> None:
    pdf_bytes = build_pdf(
        [("Titulo", 24), ("Subtitulo", 14), ("Cuerpo uno", 11), ("Cuerpo dos", 11)]
    )

    result = extract_markdown_from_pdf_bytes(pdf_bytes, ocr_enabled=False)

    assert result["content"] == "# Titulo\n\n## Subtitulo\n\nCuerpo uno\n\nCuerpo dos"


def test_extract_markdown_skips_ocr_when_disabled(monkeypatch, pdf_with_image) -> None:
    monkeypatch.setattr(pdf_service, "_extract_text_from_image_bytes", _fail_ocr)

    result = extract_markdown_from_pdf_bytes(pdf_with_image, ocr_enabled=False)

    assert result["content"] == "Texto normal"


def test_extract_markdown_runs_ocr_when_enabled(monkeypatch, pdf_with_image) -> None:
    monkeypatch.setattr(pdf_service, "_extract_text_from_image_bytes", lambda _: "texto ocr")

    result = extract_markdown_from_pdf_bytes(pdf_with_image, ocr_enabled=True)

    assert result["content"] == "Texto normal\n\ntexto ocr"
