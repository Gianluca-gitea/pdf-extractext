import io
import fitz
import pytesseract
from PIL import Image

class InvalidPDFError(ValueError):
    pass

def extract_text_from_pdf_bytes(file_bytes: bytes):
    if not file_bytes.startswith(b"%PDF-"):
        raise InvalidPDFError("El contenido no corresponde a un PDF valido.")
    
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise InvalidPDFError("El contenido no corresponde a un PDF valido.") from exc
    
    extracted_text = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        page_dict = page.get_text("dict", sort=True)
        blocks = page_dict.get("blocks", [])
        
        for block in blocks:
            if block.get("type") == 0:
                block_text = []
                
                for line in block.get("lines", []):
                    line_text = "".join(span.get("text", "") for span in line.get("spans", []))
                    if line_text.strip():
                        block_text.append(line_text)
                
                final_text = "\n".join(block_text).strip()
                if final_text:
                    extracted_text.append(final_text)
                    
            elif block.get("type") == 1:
                image_bytes = block.get("image")
                if image_bytes:
                    try:
                        image = Image.open(io.BytesIO(image_bytes))
                        ocr_text = pytesseract.image_to_string(image).strip()
                        
                        if ocr_text:
                            extracted_text.append(ocr_text)
                    except Exception:
                        pass
                
    text_txt = "\n".join(extracted_text).strip()
    
    with open("extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(text_txt)
        
    return text_txt