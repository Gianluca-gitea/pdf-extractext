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


def extract_text_from_pdf_bytes(file_bytes: bytes):
    if not file_bytes.startswith(b"%PDF-"):
        raise InvalidPDFError(INVALID_PDF_CONTENT_ERROR)
    
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise InvalidPDFError(INVALID_PDF_CONTENT_ERROR) from exc
    
    extracted_text = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        page_dict = page.get_text("dict", sort=True)
        blocks = page_dict.get("blocks", [])
        
        for block in blocks:
            block_type = block.get("type")
            if block_type == TEXT_BLOCK:
                block_text = []
                
                for line in block.get("lines", []):
                    line_text = _join_spans(line)
                    if line_text.strip():
                        block_text.append(line_text)
                
                final_text = _join_text_rows(block_text)
                if final_text:
                    extracted_text.append(final_text)
                    
            elif block_type == IMAGE_BLOCK:
                ocr_text = _extract_text_from_image_bytes(block.get("image"))
                if ocr_text:
                    extracted_text.append(ocr_text)
                
    text_txt = _join_text_rows(extracted_text)
    
    with open("extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(text_txt)
        
    return text_txt