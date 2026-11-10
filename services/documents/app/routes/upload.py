from app.messages import (
    SERVICE_BUSY_ERROR_DETAIL as SERVICE_BUSY_ERROR_DETAIL,
    INVALID_CONTENT_TYPE_ERROR_DETAIL as INVALID_CONTENT_TYPE_ERROR_DETAIL,
    MAX_FILE_SIZE_ERROR_TEMPLATE as MAX_FILE_SIZE_ERROR_TEMPLATE,
    EMPTY_FILE_ERROR_DETAIL as EMPTY_FILE_ERROR_DETAIL,
)
import logging
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from app.services.extract_client import (
    ExtractServiceBusyError,
    ExtractServiceTimeoutError,
    ExtractServiceUnavailableError,
    InvalidPDFError,
)
from app.services.upload_service import process_pdf_upload
from app.models import UploadResponse
from app.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter()


def _ensure_valid_size(file_bytes: bytes, filename: str) -> None:
    if not file_bytes:
        logger.warning("Rejected PDF: archivo vacío. filename=%s", filename)
        raise HTTPException(status_code=400, detail=EMPTY_FILE_ERROR_DETAIL)

    if len(file_bytes) > settings.max_pdf_size_bytes:
        logger.warning(
            "Rejected PDF: archivo demasiado grande. filename=%s size_bytes=%d max_size=%d",
            filename,
            len(file_bytes),
            settings.max_pdf_size_bytes,
        )
        raise HTTPException(
            status_code=413,
            detail=MAX_FILE_SIZE_ERROR_TEMPLATE.format(max_size=settings.max_pdf_size_bytes),
        )


@router.post("/documents/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)) -> UploadResponse:
    file_bytes = await file.read(settings.max_pdf_size_bytes + 1)
    filename = file.filename or "sin_nombre.pdf"
    logger.info(
        "Upload request received: filename=%s content_type=%s size_bytes=%d",
        filename,
        file.content_type,
        len(file_bytes),
    )

    _ensure_valid_size(file_bytes, filename)

    if file.content_type != "application/pdf":
        logger.warning(
            "Upload failed: tipo de contenido inválido. filename=%s content_type=%s",
            filename,
            file.content_type,
        )
        raise HTTPException(status_code=400, detail=INVALID_CONTENT_TYPE_ERROR_DETAIL)

    try:
        result = await run_in_threadpool(
            process_pdf_upload,
            file_name=filename,
            file_bytes=file_bytes,
        )
    except InvalidPDFError as exc:
        logger.warning("Invalid PDF content for filename=%s: %s", filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ExtractServiceBusyError as exc:
        logger.warning("Upload rejected: servicio de extracción saturado. filename=%s", filename)
        raise HTTPException(
            status_code=503,
            detail=SERVICE_BUSY_ERROR_DETAIL,
            headers={"Retry-After": exc.retry_after},
        ) from exc
    except ExtractServiceTimeoutError as exc:
        logger.error("Upload failed: extracción sin respuesta. filename=%s", filename)
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except ExtractServiceUnavailableError as exc:
        logger.error("Upload failed: servicio de extracción caído. filename=%s", filename)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    logger.info(
        "Upload processed successfully: filename=%s document_id=%s size_bytes=%d",
        filename,
        result.document_id,
        len(file_bytes),
    )

    return UploadResponse(
        filename=filename,
        content_type=file.content_type,
        size_bytes=len(file_bytes),
        extracted_text=result.document.txt_contenido,
        status="uploaded",
    )
