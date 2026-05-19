import io
import fitz
import pytesseract
from PIL import Image

class InvalidPDFError(ValueError):
    pass

INVALID_PDF_CONTENT_ERROR = "El contenido no corresponde a un PDF valido."


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
        
        page_text = page.get_text().strip()
        
        if page_text:
            extracted_text.append(page_text)
            
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            imgref = img[0]
            
            base_image = doc.extract_image(imgref)
            image_bytes = base_image["image"]
            
            image = Image.open(io.BytesIO(image_bytes))
            
            ocr_text = pytesseract.image_to_string(image).strip()
            
            if ocr_text:
                extracted_text.append(ocr_text)
                
    text_txt = "\n".join(extracted_text).strip()
    
    with open("extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(text_txt)
        
    return text_txt