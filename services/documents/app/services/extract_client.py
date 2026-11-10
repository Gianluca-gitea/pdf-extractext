from __future__ import annotations

from app.errors import (
    InvalidPDFError as InvalidPDFError,
    ExtractServiceBusyError as ExtractServiceBusyError,
    ExtractServiceUnavailableError as ExtractServiceUnavailableError,
    ExtractServiceTimeoutError as ExtractServiceTimeoutError,
)

import logging
from functools import lru_cache

import httpx

from app.models import ExtractionResult
from app.settings import get_settings

logger = logging.getLogger(__name__)

EXTRACT_TEXT_PATH = "/extract/text"


@lru_cache(maxsize=1)
def get_extract_client() -> httpx.Client:
    settings = get_settings()
    logger.info(
        "Starting extract client: base_url=%s timeout_s=%d",
        settings.extract_service_url,
        settings.extract_timeout_s,
    )
    return httpx.Client(base_url=settings.extract_service_url, timeout=settings.extract_timeout_s)


def close_extract_client() -> None:
    if get_extract_client.cache_info().currsize:
        get_extract_client().close()
        get_extract_client.cache_clear()
        logger.info("Extract client closed")


def _error_detail(response: httpx.Response) -> str:
    try:
        return str(response.json()["detail"])
    except ValueError, KeyError, TypeError:
        return response.text


def extract_text(file_bytes: bytes, *, client: httpx.Client | None = None) -> str:
    active_client = client or get_extract_client()
    logger.debug("Requesting text extraction: size_bytes=%d", len(file_bytes))

    try:
        response = active_client.post(
            EXTRACT_TEXT_PATH,
            content=file_bytes,
            headers={"Content-Type": "application/pdf"},
        )
    except httpx.TimeoutException as exc:
        logger.error("Extract service timed out: %s", exc)
        raise ExtractServiceTimeoutError(
            "El servicio de extracción no respondió a tiempo."
        ) from exc
    except httpx.TransportError as exc:
        logger.error("Extract service unreachable: %s", exc)
        raise ExtractServiceUnavailableError(
            "No se pudo contactar al servicio de extracción."
        ) from exc

    if response.status_code == 400:
        raise InvalidPDFError(_error_detail(response))

    if response.status_code == 503:
        logger.warning("Extract service busy")
        raise ExtractServiceBusyError(response.headers.get("Retry-After", "1"))

    if response.status_code != 200:
        logger.error(
            "Extract service failed: status_code=%d",
            response.status_code,
        )
        raise ExtractServiceUnavailableError(
            f"El servicio de extracción respondió {response.status_code}."
        )

    try:
        return ExtractionResult.model_validate(response.json()).content
    except ValueError as exc:
        raise ExtractServiceUnavailableError(
            "Respuesta invalida del servicio de extraccion."
        ) from exc
