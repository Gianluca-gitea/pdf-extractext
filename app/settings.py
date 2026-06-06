import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DEFAULT_MAX_PDF_SIZE_BYTES = 5_242_880


@dataclass(frozen=True)
class Settings:
    app_name: str = "PDF Extractext API"
    app_version: str = "0.1.0"
    app_env: str = "dev"
    max_pdf_size_bytes: int = DEFAULT_MAX_PDF_SIZE_BYTES
    # MongoDB Configuration
    mongodb_uri: str = ""
    mongodb_db_name: str = "pdf-extractext"


def get_settings() -> Settings:
    logger.debug("Loading application settings from environment")

    max_pdf_size_raw = os.getenv("APP_MAX_PDF_SIZE_BYTES")
    if max_pdf_size_raw is not None:
        try:
            max_pdf_size = int(max_pdf_size_raw)
            if max_pdf_size <= 0:
                logger.warning(
                    "APP_MAX_PDF_SIZE_BYTES must be strictly positive (got %d). Falling back to default: %d",
                    max_pdf_size,
                    DEFAULT_MAX_PDF_SIZE_BYTES,
                )
                max_pdf_size = DEFAULT_MAX_PDF_SIZE_BYTES
        except ValueError:
            logger.warning(
                "Invalid APP_MAX_PDF_SIZE_BYTES value provided: '%s'. Falling back to default: %d",
                max_pdf_size_raw,
                DEFAULT_MAX_PDF_SIZE_BYTES,
                exc_info=True,
            )
            max_pdf_size = DEFAULT_MAX_PDF_SIZE_BYTES
    else:
        logger.debug("APP_MAX_PDF_SIZE_BYTES not set. Using default: %d", DEFAULT_MAX_PDF_SIZE_BYTES)
        max_pdf_size = DEFAULT_MAX_PDF_SIZE_BYTES

    settings = Settings(
        app_name=os.getenv("APP_NAME", "PDF Extractext API"),
        app_version=os.getenv("APP_VERSION", "0.1.0"),
        app_env=os.getenv("APP_ENV", "dev"),
        max_pdf_size_bytes=max_pdf_size,
        mongodb_uri=os.getenv("MONGODB_URI", ""),
        mongodb_db_name=os.getenv("MONGODB_DB_NAME", "pdf-extractext"),
    )

    logger.info(
        "Settings loaded successfully: app_name='%s' app_env='%s' version='%s' max_pdf_size_bytes=%d",
        settings.app_name,
        settings.app_env,
        settings.app_version,
        settings.max_pdf_size_bytes,
    )

    return settings
