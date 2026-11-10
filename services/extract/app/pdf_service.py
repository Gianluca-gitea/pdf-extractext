from __future__ import annotations

import io
import logging
from app.markdown import format_markdown
from app.models import ExtractionResult
from app.pdf_reader import _read_blocks
from app.errors import InvalidPDFError as InvalidPDFError
from app.messages import INVALID_PDF_CONTENT_ERROR as INVALID_PDF_CONTENT_ERROR

__all__ = [
    "InvalidPDFError",
    "INVALID_PDF_CONTENT_ERROR",
    "extract_text_from_pdf_bytes",
    "extract_markdown_from_pdf_bytes",
]

logger = logging.getLogger(__name__)


TEXT_BLOCK = 0
IMAGE_BLOCK = 1


def _join_spans(line: dict) -> str:
    return "".join(span.get("text", "") for span in line.get("spans", []))


def _join_text_rows(rows: list[str]) -> str:
    return "\n".join(rows).strip()


def _extract_text_from_image_bytes(image_bytes: bytes | None) -> str:
    logger.debug(
        "Extracting text from image bytes: present=%s size=%d",
        bool(image_bytes),
        len(image_bytes) if image_bytes else 0,
    )

    if not image_bytes:
        logger.debug("No image bytes to extract OCR from")
        return ""

    try:
        try:
            import pytesseract
            from PIL import Image
        except Exception as exc:
            logger.warning("OCR dependencies not available: %s", exc)
            return ""

        image = Image.open(io.BytesIO(image_bytes))
        text: str = pytesseract.image_to_string(image)
        return text.strip()
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
        lines = [_join_spans(line).strip() for line in block.get("lines", [])]
        valid_lines = [line for line in lines if line]
        joined_text = _join_text_rows(valid_lines)
        return [joined_text] if joined_text else []

    if block_type == IMAGE_BLOCK:
        ocr_text = _extract_text_from_image_bytes(block.get("image"))
        return [ocr_text] if ocr_text else []

    return []


def extract_text_from_pdf_bytes(file_bytes: bytes, *, ocr_enabled: bool) -> ExtractionResult:
    logger.info("Starting PDF text extraction: bytes=%d ocr=%s", len(file_bytes), ocr_enabled)
    blocks, page_count = _read_blocks(file_bytes, ocr_enabled)

    text_txt = _join_text_rows(
        [text for block in blocks for text in _extract_text_from_block(block)]
    )
    logger.info("Extraction complete: pages=%d chars=%d", page_count, len(text_txt))
    return ExtractionResult(content=text_txt, page_count=page_count)


def extract_markdown_from_pdf_bytes(
    file_bytes: bytes, *, ocr_enabled: bool
) -> ExtractionResult:
    logger.info("Starting PDF markdown extraction: bytes=%d ocr=%s", len(file_bytes), ocr_enabled)

    blocks, page_count = _read_blocks(file_bytes, ocr_enabled)
    content = format_markdown(blocks, [_extract_text_from_block(block) for block in blocks])
    logger.info("Markdown extraction complete: pages=%d chars=%d", page_count, len(content))
    return ExtractionResult(content=content, page_count=page_count)
