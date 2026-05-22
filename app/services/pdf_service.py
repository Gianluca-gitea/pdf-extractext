from __future__ import annotations

import io
import logging

from time import perf_counter
from typing import Any

import fitz

from app.repositories.document_repository import DocumentRepository
from app.services.checksum_service import calc_checksum
from app.services.document_builder import construir_documento
from pathlib import Path


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class InvalidPDFError(ValueError):
    pass


INVALID_PDF_CONTENT_ERROR = "El contenido no corresponde a un PDF valido."
TEXT_BLOCK = 0
IMAGE_BLOCK = 1


def _join_spans(line: dict) -> str:
    return "".join(span.get("text", "") for span in line.get("spans", []))


def _join_text_rows(rows: list[str]) -> str:
    return "\n".join(rows).strip()


def _extract_text_from_image_bytes(image_bytes: bytes | None) -> str:
    logger.debug("Extracting text from image bytes: present=%s size=%d", bool(image_bytes), len(image_bytes) if image_bytes else 0)

    if not image_bytes:
        logger.debug("No image bytes to extract OCR from")
        return ""

    try:
        try:
            from PIL import Image
            import pytesseract
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.warning("OCR dependencies not available: %s", exc)
            return ""

        image = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(image).strip()
    except Exception as exc:
        logger.warning(
            "OCR failed for image block: %s",
            exc,
            exc_info=True,
        )
        return ""


def _extract_text_from_block(block: dict) -> list[str]:
    block_type = block.get("type")
    logger.debug("Extracting text from block: type=%s", block_type)
    if block_type == TEXT_BLOCK:
        lines = [
            _join_spans(line).strip()
            for line in block.get("lines", [])
        ]
        valid_lines = [line for line in lines if line]
        joined_text = _join_text_rows(valid_lines)
        return [joined_text] if joined_text else []

    if block_type == IMAGE_BLOCK:
        ocr_text = _extract_text_from_image_bytes(block.get("image"))
        return [ocr_text] if ocr_text else []

    return []


def _extract_text_from_page(page) -> list[str]:
    page_dict = page.get_text("dict", sort=True)
    blocks = page_dict.get("blocks", [])
    logger.debug("Extracting text from page: blocks=%d", len(blocks))
    return [
        text
        for block in blocks
        for text in _extract_text_from_block(block)
    ]


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    logger.info("Starting PDF text extraction: bytes=%d", len(file_bytes))

    if not file_bytes.startswith(b"%PDF-"):
        raise InvalidPDFError(INVALID_PDF_CONTENT_ERROR)

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise InvalidPDFError(INVALID_PDF_CONTENT_ERROR) from exc

    logger.info("Opened PDF stream: pages=%d", len(doc))

    extracted_text = [
        text
        for page_num in range(len(doc))
        for text in _extract_text_from_page(doc.load_page(page_num))
    ]

    text_txt = _join_text_rows(extracted_text)
    logger.info("Extraction complete: pages=%d chars=%d", len(doc), len(text_txt))
    return text_txt


def _save_text_to_disk(file_name: str, text: str) -> str:
    base = Path(file_name).stem
    txt_name = f"{base}.txt"
    try:
        Path(txt_name).write_text(text, encoding="utf-8")
        logger.info("Saved extracted text to %s", txt_name)
    except Exception as exc:
        logger.warning("Failed to save extracted text to %s: %s", txt_name, exc)
    return txt_name


def process_pdf_upload(
    *,
    file_name: str,
    file_bytes: bytes,
    repository: DocumentRepository | None = None,
) -> dict[str, Any]:
    started_at = perf_counter()
    checksum = calc_checksum(file_bytes)
    logger.info(
        "Processing PDF upload: filename=%s checksum=%s size_bytes=%d",
        file_name,
        checksum,
        len(file_bytes),
    )

    active_repository = repository or DocumentRepository()
    existing = active_repository.find_by_checksum(checksum)
    if existing is not None:
        logger.info(
            "Duplicate document detected: filename=%s checksum=%s existing_id=%s",
            file_name,
            checksum,
            existing.get("_id"),
        )
        
        texto_extraido = existing.get("txt_contenido", "")
        _save_text_to_disk(file_name, texto_extraido)
        return {
            "document_id": str(existing.get("_id", "")),
            "document": existing,
        }

    texto_extraido = extract_text_from_pdf_bytes(file_bytes)
    logger.debug(
        "Extracted text length=%d for filename=%s",
        len(texto_extraido),
        file_name,
    )

    _save_text_to_disk(file_name, texto_extraido)

    duration_ms = int((perf_counter() - started_at) * 1000)

    document = construir_documento(
        pdf_nombre=file_name,
        texto_extraido=texto_extraido,
        checksum_archivo=checksum,
        duracion_ms=duration_ms,
    )

    inserted_id = active_repository.save_document(document)
    logger.info(
        "Saved new document: filename=%s checksum=%s inserted_id=%s duration_ms=%d",
        file_name,
        checksum,
        inserted_id,
        duration_ms,
    )

    return {
        "document_id": str(inserted_id),
        "document": document,
    }
