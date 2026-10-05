import os
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DEFAULT_MAX_PDF_SIZE_BYTES = 10_485_760
DEFAULT_EXTRACT_WORKERS = 1
DEFAULT_MAX_PENDING_EXTRACTIONS = 100


@dataclass(frozen=True)
class Settings:
    app_name: str = "PDF Extractext API"
    app_version: str = "0.1.0"
    app_env: str = "dev"
    max_pdf_size_bytes: int = DEFAULT_MAX_PDF_SIZE_BYTES
    ocr_enabled: bool = False
    extract_workers: int = DEFAULT_EXTRACT_WORKERS
    max_pending_extractions: int = DEFAULT_MAX_PENDING_EXTRACTIONS


def _positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        logger.debug("%s not set. Using default: %d", name, default)
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("Invalid %s value provided: '%s'. Falling back to default: %d", name, raw, default)
        return default
    if value <= 0:
        logger.warning(
            "%s must be strictly positive (got %d). Falling back to default: %d", name, value, default
        )
        return default
    return value


def get_settings() -> Settings:
    logger.debug("Loading application settings from environment")

    settings = Settings(
        app_name=os.getenv("APP_NAME", "PDF Extractext API"),
        app_version=os.getenv("APP_VERSION", "0.1.0"),
        app_env=os.getenv("APP_ENV", "dev"),
        max_pdf_size_bytes=_positive_int_env("APP_MAX_PDF_SIZE_BYTES", DEFAULT_MAX_PDF_SIZE_BYTES),
        ocr_enabled=os.getenv("APP_OCR_ENABLED", "false").lower() == "true",
        extract_workers=_positive_int_env("APP_EXTRACT_WORKERS", DEFAULT_EXTRACT_WORKERS),
        max_pending_extractions=_positive_int_env(
            "APP_MAX_PENDING_EXTRACTIONS", DEFAULT_MAX_PENDING_EXTRACTIONS
        ),
    )

    logger.info(
        "Settings loaded successfully: app_name='%s' app_env='%s' version='%s' max_pdf_size_bytes=%d "
        "ocr_enabled=%s extract_workers=%d max_pending_extractions=%d",
        settings.app_name,
        settings.app_env,
        settings.app_version,
        settings.max_pdf_size_bytes,
        settings.ocr_enabled,
        settings.extract_workers,
        settings.max_pending_extractions,
    )

    return settings
