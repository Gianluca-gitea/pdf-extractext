from io import BytesIO
import tempfile
import os

import ocrmypdf

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class InvalidPDFError(ValueError):
    pass

def extract_text_from_pdf_bytes(file_bytes: bytes):
    if not file_bytes.startswith(b"%PDF-"):
        raise InvalidPDFError("El contenido no corresponde a un PDF valido.")

    # Crear archivos temporales para OCR
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_input:
        tmp_input.write(file_bytes)
        tmp_input_path = tmp_input.name
    
    tmp_output_path = tmp_input_path.replace('.pdf', '_ocr.pdf')
    
    try:
        # Procesar PDF con OCR
        ocrmypdf.ocr(tmp_input_path, tmp_output_path, language="eng+spa", redo_ocr=True)
        
        # Leer el PDF procesado
        with open(tmp_output_path, 'r+b') as f:
            processed_bytes = f.read()
        
        reader = PdfReader(BytesIO(processed_bytes))
    except (PdfReadError, ValueError) as exc:
        raise InvalidPDFError("El contenido no corresponde a un PDF valido.") from exc
    finally:
        # Limpiar archivos temporales
        if os.path.exists(tmp_input_path):
            os.remove(tmp_input_path)
        if os.path.exists(tmp_output_path):
            os.remove(tmp_output_path)

    pages_text = [(page.extract_text() or "").strip() for page in reader.pages]
    text_txt = "\n".join(text for text in pages_text if text).strip()

    with open('archivo.txt', 'w', encoding='utf-8') as f:
        f.write(text_txt)
        return text_txt