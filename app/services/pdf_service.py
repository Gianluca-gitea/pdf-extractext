from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class InvalidPDFError(ValueError):
    pass


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    if not file_bytes.startswith(b"%PDF-"):
        raise InvalidPDFError("El contenido no corresponde a un PDF valido.")

    try:
        reader = PdfReader(BytesIO(file_bytes))
    except (PdfReadError, ValueError) as exc:
        raise InvalidPDFError("El contenido no corresponde a un PDF valido.") from exc

    pages_text = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n".join(text for text in pages_text if text).strip()
