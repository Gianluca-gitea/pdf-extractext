from __future__ import annotations

import logging

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.settings import get_settings
from app.services.pdf_service import InvalidPDFError, process_pdf_upload

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger().setLevel(logging.INFO)

from dotenv import load_dotenv

load_dotenv()

EMPTY_FILE_ERROR_DETAIL = "El archivo está vacio."
MAX_FILE_SIZE_ERROR_TEMPLATE = "El archivo supera el tamaño máximo permitido de {max_size} bytes."
INVALID_CONTENT_TYPE_ERROR_DETAIL = "El archivo debe enviarse como application/pdf."


settings = get_settings()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
app = FastAPI(title=settings.app_name, version=settings.app_version)


@app.get("/health")
def health() -> dict[str, str]:
    logger.debug("Health check requested")
    return {"status": "ok"}


@app.post("/documents/upload")
async def upload_pdf(file: UploadFile = File(...)) -> dict[str, str | int]:
    file_bytes = await file.read()
    filename = file.filename or "sin_nombre.pdf"
    logger.info(
        "Upload request received: filename=%s content_type=%s size_bytes=%d",
        filename,
        file.content_type,
        len(file_bytes),
    )

    if not file_bytes:
        logger.warning("Upload failed: archivo vacío. filename=%s", filename)
        raise HTTPException(status_code=400, detail=EMPTY_FILE_ERROR_DETAIL)

    if len(file_bytes) > settings.max_pdf_size_bytes:
        logger.warning(
            "Upload failed: archivo demasiado grande. filename=%s size_bytes=%d max_size=%d",
            filename,
            len(file_bytes),
            settings.max_pdf_size_bytes,
        )
        raise HTTPException(
            status_code=413,
            detail=MAX_FILE_SIZE_ERROR_TEMPLATE.format(max_size=settings.max_pdf_size_bytes),
        )

    if file.content_type != "application/pdf":
        logger.warning(
            "Upload failed: tipo de contenido inválido. filename=%s content_type=%s",
            filename,
            file.content_type,
        )
        raise HTTPException(status_code=400, detail=INVALID_CONTENT_TYPE_ERROR_DETAIL)

    try:
        result = process_pdf_upload(
            file_name=filename,
            file_bytes=file_bytes,
        )
    except InvalidPDFError as exc:
        logger.warning("Invalid PDF content for filename=%s: %s", filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(
        "Upload processed successfully: filename=%s document_id=%s size_bytes=%d",
        filename,
        result["document_id"],
        len(file_bytes),
    )

    return {
        "filename": filename,
        "content_type": file.content_type,
        "size_bytes": len(file_bytes),
        "extracted_text": result["document"]["txt_contenido"],
        "status": "uploaded",
    }
