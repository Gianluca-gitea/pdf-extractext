from __future__ import annotations

import io
import logging
from collections import Counter

import fitz

logger = logging.getLogger(__name__)


class InvalidPDFError(ValueError):
    pass


INVALID_PDF_CONTENT_ERROR = "El contenido no corresponde a un PDF valido."
TEXT_BLOCK = 0
IMAGE_BLOCK = 1
TEXT_ONLY_FLAGS = fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES
H1_SIZE_RATIO = 1.5
H2_SIZE_RATIO = 1.2


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


def _open_pdf(file_bytes: bytes) -> fitz.Document:
    if not file_bytes.startswith(b"%PDF-"):
        raise InvalidPDFError(INVALID_PDF_CONTENT_ERROR)

    try:
        return fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise InvalidPDFError(INVALID_PDF_CONTENT_ERROR) from exc


def _read_blocks(file_bytes: bytes, ocr_enabled: bool) -> tuple[list[dict], int]:
    flags = fitz.TEXTFLAGS_DICT if ocr_enabled else TEXT_ONLY_FLAGS
    with _open_pdf(file_bytes) as doc:
        blocks = [
            block
            for page in doc
            for block in page.get_text("dict", flags=flags, sort=True).get("blocks", [])
        ]
        logger.info("Opened PDF stream: pages=%d blocks=%d", doc.page_count, len(blocks))
        return blocks, doc.page_count


def extract_text_from_pdf_bytes(file_bytes: bytes, *, ocr_enabled: bool) -> dict[str, str | int]:
    logger.info("Starting PDF text extraction: bytes=%d ocr=%s", len(file_bytes), ocr_enabled)
    blocks, page_count = _read_blocks(file_bytes, ocr_enabled)

    text_txt = _join_text_rows(
        [text for block in blocks for text in _extract_text_from_block(block)]
    )
    logger.info("Extraction complete: pages=%d chars=%d", page_count, len(text_txt))
    return {"content": text_txt, "page_count": page_count}


def _span_sizes(block: dict) -> list[tuple[float, int]]:
    return [
        (round(span["size"], 1), len(span["text"].strip()))
        for line in block.get("lines", [])
        for span in line["spans"]
        if span["text"].strip()
    ]


def _body_font_size(blocks: list[dict]) -> float:
    chars_by_size: Counter[float] = Counter()
    for block in blocks:
        for size, chars in _span_sizes(block):
            chars_by_size[size] += chars
    return chars_by_size.most_common(1)[0][0] if chars_by_size else 0.0


def _to_markdown(block: dict, text: str, body_size: float) -> str:
    sizes = [size for size, _ in _span_sizes(block)]
    ratio = max(sizes) / body_size if sizes else 0
    if ratio >= H1_SIZE_RATIO:
        return "# " + text.replace("\n", " ")
    if ratio >= H2_SIZE_RATIO:
        return "## " + text.replace("\n", " ")
    return text


def extract_markdown_from_pdf_bytes(
    file_bytes: bytes, *, ocr_enabled: bool
) -> dict[str, str | int]:
    logger.info("Starting PDF markdown extraction: bytes=%d ocr=%s", len(file_bytes), ocr_enabled)

    blocks, page_count = _read_blocks(file_bytes, ocr_enabled)
    body_size = _body_font_size(blocks)
    content = "\n\n".join(
        _to_markdown(block, text, body_size)
        for block in blocks
        for text in _extract_text_from_block(block)
    )
    logger.info("Markdown extraction complete: pages=%d chars=%d", page_count, len(content))
    return {"content": content, "page_count": page_count}
