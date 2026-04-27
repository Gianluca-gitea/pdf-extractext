import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "PDF Extractext API"
    app_version: str = "0.1.0"
    app_env: str = "dev"
    max_pdf_size_bytes: int = 5_242_880


def _read_positive_int_env(var_name: str, default: int) -> int:
    raw_value = os.getenv(var_name)
    if raw_value is None:
        return default

    try:
        parsed = int(raw_value)
    except ValueError:
        return default

    return parsed if parsed > 0 else default


def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "PDF Extractext API"),
        app_version=os.getenv("APP_VERSION", "0.1.0"),
        app_env=os.getenv("APP_ENV", "dev"),
        max_pdf_size_bytes=_read_positive_int_env("APP_MAX_PDF_SIZE_BYTES", 5_242_880),
    )
