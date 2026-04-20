from pypdf import PdfReader
import fitz

doc = fitz.open('ejemplo.pdf')
text = ""
for page in doc:
   text+=page.get_text()
print(text)

