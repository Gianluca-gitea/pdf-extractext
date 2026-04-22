from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_upload_pdf_accepts_real_file() -> None:
    files = {"file": ("documento.pdf", b"%PDF-1.4\ncontenido", "application/pdf")}

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 200
    assert response.json() == {
        "filename": "documento.pdf",
        "content_type": "application/pdf",
        "size_bytes": len(b"%PDF-1.4\ncontenido"),
        "status": "uploaded",
    }


def test_upload_pdf_rejects_non_pdf_file() -> None:
    files = {"file": ("texto.txt", b"hola", "text/plain")}

    response = client.post("/documents/upload", files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": "El archivo debe ser un PDF."}
