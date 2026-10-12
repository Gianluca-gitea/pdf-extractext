from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from functools import lru_cache
from time import perf_counter

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from starlette.datastructures import UploadFile as FormFile
from starlette.formparsers import MultiPartParser

from app import __version__
from app.logging_config import configure_logging
from app.pdf_service import (
    InvalidPDFError,
    extract_markdown_from_pdf_bytes,
    extract_text_from_pdf_bytes,
)
from app.settings import get_settings

load_dotenv()

EMPTY_FILE_ERROR_DETAIL = "El archivo está vacio."
MAX_FILE_SIZE_ERROR_TEMPLATE = "El archivo supera el tamaño máximo permitido de {max_size} bytes."
MISSING_FILE_FIELD_ERROR_DETAIL = "Falta el campo 'file' con el PDF."
SERVICE_BUSY_ERROR_DETAIL = "Servicio saturado, reintentá en unos segundos."

Extractor = Callable[..., dict[str, str | int]]

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)
logger.info("Settings loaded: %s", settings)
MultiPartParser.spool_max_size = sys.maxsize


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    shutdown_extraction_pool()


app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
_pending_extractions = 0


@app.get("/health")
def health() -> dict[str, str]:
    logger.debug("Health check requested")
    return {"status": "ok"}


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
        return await request.body(), "raw"

    async with request.form() as form:
        upload = form.get("file")
        if not isinstance(upload, FormFile):
            logger.warning("Rejected extract request: multipart sin campo 'file'")
            raise HTTPException(status_code=400, detail=MISSING_FILE_FIELD_ERROR_DETAIL)
        return await upload.read(), upload.filename or "multipart"


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


@app.post("/extract")
async def extract(request: Request) -> dict[str, str | int]:
    return await _run_extraction(request, extract_markdown_from_pdf_bytes)


@app.post("/extract/text")
async def extract_text(request: Request) -> dict[str, str | int]:
    return await _run_extraction(request, extract_text_from_pdf_bytes)
