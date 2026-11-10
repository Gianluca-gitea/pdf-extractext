from app.messages import (
    NO_UPDATE_FIELDS_ERROR_DETAIL as NO_UPDATE_FIELDS_ERROR_DETAIL,
    INVALID_DOCUMENT_ID_ERROR_DETAIL as INVALID_DOCUMENT_ID_ERROR_DETAIL,
)
from app.models import DocumentUpdate, DocumentResponse, DocumentList, DeleteResponse
import logging
from datetime import datetime
from urllib.parse import quote
from bson.errors import InvalidId
from bson.objectid import ObjectId
from app.messages import (
    DOCUMENT_NOT_FOUND as DOCUMENT_NOT_FOUND,
)
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from app.services.document_service import DocumentService, InvalidStatusTransitionError

logger = logging.getLogger(__name__)
router = APIRouter()
MAX_LIST_LIMIT = 100


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


def _parse_document_id(document_id: str) -> ObjectId:
    try:
        return ObjectId(document_id)
    except (InvalidId, TypeError) as exc:
        logger.warning("Invalid document ID format: %s. Error: %s", document_id, exc)
        raise HTTPException(status_code=400, detail=INVALID_DOCUMENT_ID_ERROR_DETAIL) from exc


@router.get(
    "/documents/by-checksum/{checksum}",
    response_model=DocumentResponse,
    response_model_exclude_unset=True,
)
def get_document_by_checksum(checksum: str) -> dict[str, object]:
    logger.info("Requested document by checksum: %s", checksum)
    service = DocumentService()
    document = service.get_document_by_checksum(checksum)

    if document is None:
        logger.warning("Document not found for checksum: %s", checksum)
        raise HTTPException(status_code=404, detail=DOCUMENT_NOT_FOUND)

    logger.info("Document found for checksum: %s, document_id: %s", checksum, document.get("_id"))
    return {
        "document_id": str(document.get("_id", "")),
        "document": _serialize_document(document),
    }


@router.get("/documents", response_model=DocumentList, response_model_exclude_unset=True)
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


@router.get(
    "/documents/{document_id}", response_model=DocumentResponse, response_model_exclude_unset=True
)
def get_document_by_id(document_id: str, include_text: bool = True) -> dict[str, object]:
    logger.info("Requested document by id: %s", document_id)
    object_id = _parse_document_id(document_id)
    service = DocumentService()
    document = service.get_document_by_id(object_id, include_text=include_text)

    if document is None:
        logger.warning("Document not found for id: %s", document_id)
        raise HTTPException(status_code=404, detail=DOCUMENT_NOT_FOUND)

    return {
        "document_id": str(document.get("_id", "")),
        "document": _serialize_document(document),
    }


@router.patch(
    "/documents/{document_id}", response_model=DocumentResponse, response_model_exclude_unset=True
)
def update_document(document_id: str, payload: DocumentUpdate) -> dict[str, object]:
    logger.info("Updating document id: %s", document_id)
    object_id = _parse_document_id(document_id)

    updates = payload.model_dump(exclude_unset=True)
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
        raise HTTPException(status_code=404, detail=DOCUMENT_NOT_FOUND)

    return {
        "document_id": str(document.get("_id", "")),
        "document": _serialize_document(document),
    }


@router.delete(
    "/documents/{document_id}", response_model=DeleteResponse, response_model_exclude_unset=True
)
def delete_document(document_id: str) -> dict[str, str]:
    logger.info("Deleting document id: %s", document_id)
    object_id = _parse_document_id(document_id)
    service = DocumentService()
    deleted = service.delete_document(object_id)

    if not deleted:
        logger.warning("Delete failed. Document not found for id: %s", document_id)
        raise HTTPException(status_code=404, detail=DOCUMENT_NOT_FOUND)

    return {
        "status": "deleted",
    }


@router.get("/documents/{document_id}/download")
def download_document_text(document_id: str) -> Response:
    logger.info("Download requested for document_id: %s", document_id)
    object_id = _parse_document_id(document_id)

    service = DocumentService()
    document = service.get_document_by_id(object_id, include_text=True)

    if document is None:
        logger.warning("Download failed: Document not found for ID: %s", document_id)
        raise HTTPException(status_code=404, detail=DOCUMENT_NOT_FOUND)

    txt_content = document.get("txt_contenido", "")
    downloaded_filename = f"{document.get('pdf_nombre', 'documento')}.txt"

    logger.info(
        "Download processed successfully for document_id: %s, filename: %s",
        document_id,
        downloaded_filename,
    )

    encoded_filename = quote(downloaded_filename, safe="")
    disposition = (
        f'attachment; filename="{downloaded_filename}"'
        if encoded_filename == downloaded_filename
        else "attachment; filename=\"documento.txt\"; filename*=UTF-8''" + encoded_filename
    )
    return Response(
        content=txt_content,
        media_type="text/plain",
        headers={
            "Content-Disposition": disposition,
        },
    )
