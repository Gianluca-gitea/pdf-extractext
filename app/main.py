from fastapi import FastAPI, File, HTTPException, UploadFile

from app.settings import get_settings
from app.services.pdf_service import InvalidPDFError, extract_text_from_pdf_bytes


settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/documents/upload")
async def upload_pdf(file: UploadFile = File(...)) -> dict[str, str | int]:
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="El archivo esta vacio.")

    if len(file_bytes) > settings.max_pdf_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"El archivo supera el tamano maximo permitido de {settings.max_pdf_size_bytes} bytes.",
        )

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="El archivo debe enviarse como application/pdf.")

    try:
        extracted_text = extract_text_from_pdf_bytes(file_bytes)
    except InvalidPDFError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "filename": file.filename or "sin_nombre.pdf",
        "content_type": file.content_type,
        "size_bytes": len(file_bytes),
        "extracted_text": extracted_text,
        "status": "uploaded",
    }
