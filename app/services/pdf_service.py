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

        blocks = page.get_text("blocks", sort=True)

        for b in blocks:
            x0, y0, x1, y1, text, block_no, block_type = b

            if block_type == 0:
                clean_text = text.strip()
                if clean_text:
                    extracted_text.append(clean_text)

            elif block_type == 1:
                try:
                    rect = fitz.Rect(x0, y0, x1, y1)

                    if rect.width < 10 or rect.height < 10:
                        continue

                    pix = page.get_pixmap(clip=rect, dpi = 300)
                    image = Image.open(io.BytesIO(pix.tobytes()))

                    ocr_text = pytesseract.image_to_string(image, lang="spa+eng")

                    if ocr_text.strip():
                        extracted_text.append(ocr_text.strip())

                except Exception:
                    continue

    text_txt = "\n".join(extracted_text).strip()
    
    with open("extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(text_txt)
        
    return text_txt