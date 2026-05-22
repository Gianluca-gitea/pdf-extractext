from __future__ import annotations

import logging

from bson.objectid import ObjectId
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from dotenv import load_dotenv

from app.repositories.document_repository import DocumentRepository
from app.settings import get_settings
from app.services.pdf_service import InvalidPDFError, process_pdf_upload

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger().setLevel(logging.INFO)

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


def _serialize_document(document: dict) -> dict:
    document_copy = {
        **document,
        "_id": str(document.get("_id", "")),
    }
    return document_copy


@app.get("/documents/by-checksum/{checksum}")
def get_document_by_checksum(checksum: str) -> dict[str, object]:
    logger.info("Requested document by checksum: %s", checksum)
    repository = DocumentRepository()
    document = repository.find_by_checksum(checksum)

    if document is None:
        logger.warning("Document not found for checksum: %s", checksum)
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    logger.info("Document found for checksum: %s, document_id: %s", checksum, document.get("_id"))
    return {
        "document_id": str(document.get("_id", "")),
        "document": _serialize_document(document),
    }


@app.get("/documents/{document_id}/download")
def download_document_text(document_id: str) -> Response:
    logger.info("Download requested for document_id: %s", document_id)
    try:
        object_id = ObjectId(document_id)
    except Exception as exc:
        logger.warning("Invalid document ID format: %s. Error: %s", document_id, exc)
        raise HTTPException(status_code=400, detail="ID de documento inválido.")

    repository = DocumentRepository()
    document = repository.find_by_id(object_id)

    if document is None:
        logger.warning("Download failed: Document not found for ID: %s", document_id)
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    txt_content = document.get("txt_contenido", "")
    downloaded_filename = f"{document.get('pdf_nombre', 'documento')}.txt"

    logger.info(
        "Download processed successfully for document_id: %s, filename: %s",
        document_id,
        downloaded_filename,
    )

    return Response(
        content=txt_content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{downloaded_filename}"',
        },
    )


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

