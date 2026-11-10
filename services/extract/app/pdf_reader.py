import logging
import fitz
from app.errors import InvalidPDFError
from app.messages import INVALID_PDF_CONTENT_ERROR

logger = logging.getLogger(__name__)
TEXT_ONLY_FLAGS = fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES


def _open_pdf(file_bytes: bytes) -> fitz.Document:
    if not file_bytes.startswith(b"%PDF-"):
        raise InvalidPDFError(INVALID_PDF_CONTENT_ERROR)

    try:
        return fitz.open(stream=file_bytes, filetype="pdf")
    except (ValueError, RuntimeError) as exc:
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
