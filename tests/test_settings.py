from app.settings import get_settings
from app.settings import (
    DEFAULT_EXTRACT_WORKERS,
    DEFAULT_MAX_PDF_SIZE_BYTES,
    DEFAULT_MAX_PENDING_EXTRACTIONS,
)


def test_get_settings_reads_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "PDF Extractext Test")
    monkeypatch.setenv("APP_VERSION", "9.9.9")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_MAX_PDF_SIZE_BYTES", "1234")

    settings = get_settings()

    assert settings.app_name == "PDF Extractext Test"
    assert settings.app_version == "9.9.9"
    assert settings.app_env == "test"
    assert settings.max_pdf_size_bytes == 1234


def test_get_settings_uses_default_when_max_size_is_negative(monkeypatch) -> None:
    monkeypatch.setenv("APP_MAX_PDF_SIZE_BYTES", "-5000")

    settings = get_settings()

    assert settings.max_pdf_size_bytes == DEFAULT_MAX_PDF_SIZE_BYTES


def test_get_settings_uses_default_when_max_size_is_invalid_string(monkeypatch) -> None:
    monkeypatch.setenv("APP_MAX_PDF_SIZE_BYTES", "un-texto-en-vez-de-numeros")

    settings = get_settings()

    assert settings.max_pdf_size_bytes == DEFAULT_MAX_PDF_SIZE_BYTES


def test_get_settings_disables_ocr_by_default(monkeypatch) -> None:
    monkeypatch.delenv("APP_OCR_ENABLED", raising=False)

    assert get_settings().ocr_enabled is False


def test_get_settings_enables_ocr_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_OCR_ENABLED", "true")

    assert get_settings().ocr_enabled is True


def test_get_settings_keeps_ocr_disabled_for_unrecognized_value(monkeypatch) -> None:
    monkeypatch.setenv("APP_OCR_ENABLED", "maybe")

    assert get_settings().ocr_enabled is False


def test_get_settings_uses_one_extract_worker_by_default(monkeypatch) -> None:
    monkeypatch.delenv("APP_EXTRACT_WORKERS", raising=False)

    assert get_settings().extract_workers == 1


def test_get_settings_reads_extraction_limits_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_EXTRACT_WORKERS", "3")
    monkeypatch.setenv("APP_MAX_PENDING_EXTRACTIONS", "12")

    settings = get_settings()

    assert settings.extract_workers == 3
    assert settings.max_pending_extractions == 12


def test_get_settings_uses_default_for_invalid_extraction_limits(monkeypatch) -> None:
    monkeypatch.setenv("APP_EXTRACT_WORKERS", "0")
    monkeypatch.setenv("APP_MAX_PENDING_EXTRACTIONS", "muchas")

    settings = get_settings()

    assert settings.extract_workers == DEFAULT_EXTRACT_WORKERS
    assert settings.max_pending_extractions == DEFAULT_MAX_PENDING_EXTRACTIONS
