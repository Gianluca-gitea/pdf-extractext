from __future__ import annotations

import logging
from collections.abc import Callable
from time import perf_counter
from typing import Any

from pymongo.errors import DuplicateKeyError

from app.repositories.document_repository import DocumentRepository, get_document_repository
from app.services.checksum_service import calc_checksum
from app.services.document_builder import construir_documento
from app.services.extract_client import extract_text

logger = logging.getLogger(__name__)


def _as_result(document: dict) -> dict[str, Any]:
    return {"document_id": str(document.get("_id", "")), "document": document}


def process_pdf_upload(
    *,
    file_name: str,
    file_bytes: bytes,
    repository: DocumentRepository | None = None,
    extractor: Callable[[bytes], str] | None = None,
) -> dict[str, Any]:
    started_at = perf_counter()
    checksum = calc_checksum(file_bytes)
    logger.info(
        "Processing PDF upload: filename=%s checksum=%s size_bytes=%d",
        file_name,
        checksum,
        len(file_bytes),
    )

    active_repository = repository or get_document_repository()
    existing = active_repository.find_by_checksum(checksum)
    if existing is not None:
        logger.info(
            "Duplicate document detected: filename=%s checksum=%s existing_id=%s",
            file_name,
            checksum,
            existing.get("_id"),
        )

        return _as_result(existing)

    active_extractor = extractor or extract_text
    texto_extraido = active_extractor(file_bytes)
    logger.debug(
        "Extracted text length=%d for filename=%s",
        len(texto_extraido),
        file_name,
    )

    duration_ms = int((perf_counter() - started_at) * 1000)

    document = construir_documento(
        pdf_nombre=file_name,
        texto_extraido=texto_extraido,
        checksum_archivo=checksum,
        duracion_ms=duration_ms,
        estado="ok",
    )

    try:
        inserted_id = active_repository.save_document(document)
    except DuplicateKeyError:
        winner = active_repository.find_by_checksum(checksum)
        if winner is None:
            raise
        logger.info("Concurrent upload already saved checksum=%s", checksum)
        return _as_result(winner)

    logger.info(
        "Saved new document: filename=%s checksum=%s inserted_id=%s duration_ms=%d",
        file_name,
        checksum,
        inserted_id,
        duration_ms,
    )

    return {
        "document_id": str(inserted_id),
        "document": document,
    }
