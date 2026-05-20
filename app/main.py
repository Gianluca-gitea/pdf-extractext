from fastapi import FastAPI, File, HTTPException, UploadFile

from app.settings import get_settings
from app.services.pdf_service import InvalidPDFError, extract_text_from_pdf_bytes


EMPTY_FILE_ERROR_DETAIL = "El archivo está vacio."
MAX_FILE_SIZE_ERROR_TEMPLATE = "El archivo supera el tamaño máximo permitido de {max_size} bytes."
INVALID_CONTENT_TYPE_ERROR_DETAIL = "El archivo debe enviarse como application/pdf."


settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/documents/upload")
async def upload_pdf(file: UploadFile = File(...)) -> dict[str, str | int]:
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail=EMPTY_FILE_ERROR_DETAIL)

    if len(file_bytes) > settings.max_pdf_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=MAX_FILE_SIZE_ERROR_TEMPLATE.format(max_size=settings.max_pdf_size_bytes),
        )

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail=INVALID_CONTENT_TYPE_ERROR_DETAIL)

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
