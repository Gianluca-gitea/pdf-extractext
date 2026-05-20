import os
from dataclasses import dataclass

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
    # Read and validate max PDF size from environment
    max_pdf_size_raw = os.getenv("APP_MAX_PDF_SIZE_BYTES")
    if max_pdf_size_raw is not None:
        try:
            max_pdf_size = int(max_pdf_size_raw)
            max_pdf_size = max_pdf_size if max_pdf_size > 0 else DEFAULT_MAX_PDF_SIZE_BYTES
        except ValueError:
            max_pdf_size = DEFAULT_MAX_PDF_SIZE_BYTES
    else:
        max_pdf_size = DEFAULT_MAX_PDF_SIZE_BYTES

    return Settings(
        app_name=os.getenv("APP_NAME", "PDF Extractext API"),
        app_version=os.getenv("APP_VERSION", "0.1.0"),
        app_env=os.getenv("APP_ENV", "dev"),
        max_pdf_size_bytes=max_pdf_size,
        mongodb_uri=os.getenv("MONGODB_URI", ""),
        mongodb_db_name=os.getenv("MONGODB_DB_NAME", "pdf-extractext"),
    )
