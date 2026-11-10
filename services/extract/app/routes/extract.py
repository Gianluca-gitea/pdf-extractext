from app.messages import (
    SERVICE_BUSY_ERROR_DETAIL as SERVICE_BUSY_ERROR_DETAIL,
    MISSING_FILE_FIELD_ERROR_DETAIL as MISSING_FILE_FIELD_ERROR_DETAIL,
    MAX_FILE_SIZE_ERROR_TEMPLATE as MAX_FILE_SIZE_ERROR_TEMPLATE,
    EMPTY_FILE_ERROR_DETAIL as EMPTY_FILE_ERROR_DETAIL,
)

import asyncio
import logging
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from time import perf_counter

from fastapi import APIRouter, HTTPException, Request
from starlette.datastructures import UploadFile as FormFile
from starlette.formparsers import MultiPartParser

from app.pdf_service import (
    InvalidPDFError,
    extract_markdown_from_pdf_bytes,
    extract_text_from_pdf_bytes,
)
from app.models import ExtractionResult
from app.settings import get_settings

Extractor = Callable[..., dict[str, str | int]]

settings = get_settings()
logger = logging.getLogger(__name__)
MultiPartParser.spool_max_size = sys.maxsize


router = APIRouter()
_pending_extractions = 0


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


async def _read_pdf_payload(request: Request) -> tuple[bytes, str]:
    if not request.headers.get("content-type", "").startswith("multipart/form-data"):
        payload = bytearray()
        async for chunk in request.stream():
            if len(payload) + len(chunk) > settings.max_pdf_size_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=MAX_FILE_SIZE_ERROR_TEMPLATE.format(
                        max_size=settings.max_pdf_size_bytes
                    ),
                )
            payload.extend(chunk)
        return bytes(payload), "raw"

    async with request.form() as form:
        upload = form.get("file")
        if not isinstance(upload, FormFile):
            logger.warning("Rejected extract request: multipart sin campo 'file'")
            raise HTTPException(status_code=400, detail=MISSING_FILE_FIELD_ERROR_DETAIL)
        return await upload.read(settings.max_pdf_size_bytes + 1), upload.filename or "multipart"


@lru_cache(maxsize=1)
def get_extraction_pool() -> ThreadPoolExecutor:
    logger.info("Starting extraction pool: workers=%d", settings.extract_workers)
    return ThreadPoolExecutor(max_workers=settings.extract_workers)


def shutdown_extraction_pool() -> None:
    if get_extraction_pool.cache_info().currsize:
        get_extraction_pool().shutdown()
        get_extraction_pool.cache_clear()
        logger.info("Extraction pool stopped")


async def _run_extraction(request: Request, extractor: Extractor) -> dict[str, str | int]:
    global _pending_extractions
    path = request.url.path
    if _pending_extractions >= settings.max_pending_extractions:
        logger.warning(
            "Rejected %s request: servicio saturado. pending=%d", path, _pending_extractions
        )
        raise HTTPException(
            status_code=503, detail=SERVICE_BUSY_ERROR_DETAIL, headers={"Retry-After": "1"}
        )

    _pending_extractions += 1
    try:
        started_at = perf_counter()
        file_bytes, source = await _read_pdf_payload(request)
        logger.info(
            "%s request received: source=%s size_bytes=%d pending=%d",
            path,
            source,
            len(file_bytes),
            _pending_extractions,
        )

        _ensure_valid_size(file_bytes, source)

        try:
            result = await asyncio.wrap_future(
                get_extraction_pool().submit(
                    extractor, file_bytes, ocr_enabled=settings.ocr_enabled
                )
            )
        except InvalidPDFError as exc:
            logger.warning("Rejected %s request: PDF inválido. source=%s", path, source)
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        logger.info(
            "%s request completed: source=%s duration_ms=%d",
            path,
            source,
            int((perf_counter() - started_at) * 1000),
        )
        return result
    finally:
        _pending_extractions -= 1


@router.post("/extract", response_model=ExtractionResult)
async def extract(request: Request) -> dict[str, str | int]:
    return await _run_extraction(request, extract_markdown_from_pdf_bytes)


@router.post("/extract/text", response_model=ExtractionResult)
async def extract_text(request: Request) -> dict[str, str | int]:
    return await _run_extraction(request, extract_text_from_pdf_bytes)
