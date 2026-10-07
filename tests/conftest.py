import fitz
import pytest


@pytest.fixture
def build_pdf():
    def _build(*pages: list[tuple[str, float]]) -> bytes:
        doc = fitz.open()
        for lines in pages:
            page = doc.new_page(width=400, height=400)
            y = 40
            for text, fontsize in lines:
                page.insert_text((20, y), text, fontsize=fontsize)
                y += fontsize * 3
        return doc.write()

    return _build


@pytest.fixture
def pdf_bytes(build_pdf) -> bytes:
    return build_pdf([("Hola extract", 11)])


@pytest.fixture
def pdf_with_image() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((20, 20), "Texto normal", fontsize=11)
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 10, 10), False)
    page.insert_image(fitz.Rect(20, 50, 120, 150), stream=pixmap.tobytes("png"))
    return doc.write()
