import pytest


@pytest.fixture
def pdf_bytes() -> bytes:
    # La extracción vive en el servicio extract: acá alcanza con bytes que parezcan un PDF.
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
