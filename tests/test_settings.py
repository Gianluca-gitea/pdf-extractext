import pytest

from app.settings import get_settings
from app.settings import DEFAULT_MAX_PDF_SIZE_BYTES
from app.settings import DEFAULT_MONGODB_URI


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


def test_get_settings_uses_local_mongo_default_in_dev(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    settings = get_settings()

    assert settings.mongodb_uri == DEFAULT_MONGODB_URI


def test_get_settings_raises_when_mongo_uri_missing_outside_local(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    with pytest.raises(RuntimeError, match="MONGODB_URI"):
        get_settings()


def test_get_settings_uses_configured_mongo_uri_outside_local(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("MONGODB_URI", "mongodb://prod-mongo:27017")

    settings = get_settings()

    assert settings.mongodb_uri == "mongodb://prod-mongo:27017"
