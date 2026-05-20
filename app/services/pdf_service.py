import io
import logging

import fitz
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

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
    if not image_bytes:
        return ""

    try:
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
    return [
        text
        for block in blocks
        for text in _extract_text_from_block(block)
    ]

def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    if not file_bytes.startswith(b"%PDF-"):
        raise InvalidPDFError(INVALID_PDF_CONTENT_ERROR)
    
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise InvalidPDFError(INVALID_PDF_CONTENT_ERROR) from exc
    
    extracted_text = []
    
    extracted_text = [
        text
        for page_num in range(len(doc))
        for text in _extract_text_from_page(doc.load_page(page_num))
    ]

    text_txt = _join_text_rows(extracted_text)

    with open("extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(text_txt)

    return text_txt