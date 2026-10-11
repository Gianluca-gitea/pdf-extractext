import os
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

DEFAULT_MAX_PDF_SIZE_BYTES = 10_485_760
DEFAULT_EXTRACT_WORKERS = 1
DEFAULT_MAX_PENDING_EXTRACTIONS = 100
DEFAULT_LOG_LEVEL = "INFO"


@dataclass(frozen=True)
class Settings:
    app_name: str = "PDF Extractext API"
    max_pdf_size_bytes: int = DEFAULT_MAX_PDF_SIZE_BYTES
    ocr_enabled: bool = False
    extract_workers: int = DEFAULT_EXTRACT_WORKERS
    max_pending_extractions: int = DEFAULT_MAX_PENDING_EXTRACTIONS
    log_level: str = DEFAULT_LOG_LEVEL
    mongodb_uri: str = field(default="mongodb://localhost:27017", repr=False)
    mongodb_db_name: str = "pdf-extractext"
    mongodb_collection_name: str = "documents"


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


def _log_level_env(name: str, default: str) -> str:
    raw = os.getenv(name, default).upper()
    if raw not in logging.getLevelNamesMapping():
        logger.warning("Invalid %s value provided: '%s'. Falling back to default: %s", name, raw, default)
        return default
    return raw


def get_settings() -> Settings:
    logger.debug("Loading application settings from environment")

    return Settings(
        app_name=os.getenv("APP_NAME", "PDF Extractext API"),
        max_pdf_size_bytes=_positive_int_env("APP_MAX_PDF_SIZE_BYTES", DEFAULT_MAX_PDF_SIZE_BYTES),
        ocr_enabled=os.getenv("APP_OCR_ENABLED", "false").lower() == "true",
        extract_workers=_positive_int_env("APP_EXTRACT_WORKERS", DEFAULT_EXTRACT_WORKERS),
        max_pending_extractions=_positive_int_env(
            "APP_MAX_PENDING_EXTRACTIONS", DEFAULT_MAX_PENDING_EXTRACTIONS
        ),
        log_level=_log_level_env("APP_LOG_LEVEL", DEFAULT_LOG_LEVEL),
        mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        mongodb_db_name=os.getenv("MONGODB_DB_NAME", "pdf-extractext"),
        mongodb_collection_name=os.getenv("MONGO_COLLECTION_NAME", "documents"),
    )
