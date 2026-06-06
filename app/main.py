from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from bson.objectid import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.services.document_service import DocumentService, InvalidStatusTransitionError
from app.services.pdf_service import InvalidPDFError, process_pdf_upload
from app.settings import get_settings

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
INVALID_DOCUMENT_ID_ERROR_DETAIL = "ID de documento inválido."
NO_UPDATE_FIELDS_ERROR_DETAIL = "No hay campos para actualizar."
MAX_LIST_LIMIT = 100


settings = get_settings()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
app = FastAPI(title=settings.app_name, version=settings.app_version)


class DocumentUpdate(BaseModel):
    pdf_nombre: str | None = Field(default=None, min_length=1, max_length=200)
    estado: Literal["pendiente", "ok", "error"] | None = None
    error: str | None = Field(default=None, max_length=500)


@app.get("/health")
def health() -> dict[str, str]:
    logger.debug("Health check requested")
    return {"status": "ok"}


def _serialize_document(document: dict) -> dict:
    document_copy = {**document}
    document_id = document_copy.get("_id")
    if document_id is not None:
        document_copy["_id"] = str(document_id)

    created_at = document_copy.get("created_at")
    if isinstance(created_at, datetime):
        document_copy["created_at"] = created_at.isoformat()

    deleted_at = document_copy.get("deleted_at")
    if isinstance(deleted_at, datetime):
        document_copy["deleted_at"] = deleted_at.isoformat()
    return document_copy


def _model_dump(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=True)
    return model.dict(exclude_unset=True)


def _parse_document_id(document_id: str) -> ObjectId:
    try:
        return ObjectId(document_id)
    except Exception as exc:
        logger.warning("Invalid document ID format: %s. Error: %s", document_id, exc)
        raise HTTPException(status_code=400, detail=INVALID_DOCUMENT_ID_ERROR_DETAIL) from exc


@app.get("/documents/by-checksum/{checksum}")
def get_document_by_checksum(checksum: str) -> dict[str, object]:
    logger.info("Requested document by checksum: %s", checksum)
    service = DocumentService()
    document = service.get_document_by_checksum(checksum)

    if document is None:
        logger.warning("Document not found for checksum: %s", checksum)
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    logger.info("Document found for checksum: %s, document_id: %s", checksum, document.get("_id"))
    return {
        "document_id": str(document.get("_id", "")),
        "document": _serialize_document(document),
    }


@app.get("/documents")
def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=MAX_LIST_LIMIT),
    include_text: bool = False,
) -> dict[str, object]:
    logger.info("Listing documents: skip=%d limit=%d include_text=%s", skip, limit, include_text)
    service = DocumentService()
    documents = service.list_documents(skip=skip, limit=limit, include_text=include_text)

    serialized_documents = [_serialize_document(document) for document in documents]
    return {
        "items": serialized_documents,
        "count": len(serialized_documents),
        "skip": skip,
        "limit": limit,
    }


@app.get("/documents/{document_id}")
def get_document_by_id(document_id: str, include_text: bool = True) -> dict[str, object]:
    logger.info("Requested document by id: %s", document_id)
    object_id = _parse_document_id(document_id)
    service = DocumentService()
    document = service.get_document_by_id(object_id, include_text=include_text)

    if document is None:
        logger.warning("Document not found for id: %s", document_id)
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    return {
        "document_id": str(document.get("_id", "")),
        "document": _serialize_document(document),
    }


@app.patch("/documents/{document_id}")
def update_document(document_id: str, payload: DocumentUpdate) -> dict[str, object]:
    logger.info("Updating document id: %s", document_id)
    object_id = _parse_document_id(document_id)

    updates = _model_dump(payload)
    if updates.get("pdf_nombre") is None:
        updates.pop("pdf_nombre", None)
    if updates.get("estado") is None:
        updates.pop("estado", None)

    if not updates:
        raise HTTPException(status_code=400, detail=NO_UPDATE_FIELDS_ERROR_DETAIL)

    service = DocumentService()
    try:
        document = service.update_document(object_id, updates)
    except InvalidStatusTransitionError as exc:
        logger.warning("Invalid status transition for document_id=%s: %s", document_id, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if document is None:
        logger.warning("Update failed. Document not found for id: %s", document_id)
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    return {
        "document_id": str(document.get("_id", "")),
        "document": _serialize_document(document),
    }


@app.delete("/documents/{document_id}")
def delete_document(document_id: str) -> dict[str, str]:
    logger.info("Deleting document id: %s", document_id)
    object_id = _parse_document_id(document_id)
    service = DocumentService()
    deleted = service.delete_document(object_id)

    if not deleted:
        logger.warning("Delete failed. Document not found for id: %s", document_id)
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    return {
        "status": "deleted",
    }


@app.get("/documents/{document_id}/download")
def download_document_text(document_id: str) -> Response:
    logger.info("Download requested for document_id: %s", document_id)
    object_id = _parse_document_id(document_id)

    service = DocumentService()
    document = service.get_document_by_id(object_id, include_text=True)

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
