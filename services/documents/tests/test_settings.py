from app.settings import get_settings
from app.settings import (
    DEFAULT_EXTRACT_SERVICE_URL,
    DEFAULT_EXTRACT_TIMEOUT_S,
    DEFAULT_MAX_PDF_SIZE_BYTES,
)


def test_get_settings_reads_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "PDF Extractext Test")
    monkeypatch.setenv("APP_MAX_PDF_SIZE_BYTES", "1234")

    settings = get_settings()

    assert settings.app_name == "PDF Extractext Test"
    assert settings.max_pdf_size_bytes == 1234


def test_get_settings_uses_default_when_max_size_is_negative(monkeypatch) -> None:
    monkeypatch.setenv("APP_MAX_PDF_SIZE_BYTES", "-5000")

    settings = get_settings()

    assert settings.max_pdf_size_bytes == DEFAULT_MAX_PDF_SIZE_BYTES


def test_get_settings_uses_default_when_max_size_is_invalid_string(monkeypatch) -> None:
    monkeypatch.setenv("APP_MAX_PDF_SIZE_BYTES", "un-texto-en-vez-de-numeros")

    settings = get_settings()

    assert settings.max_pdf_size_bytes == DEFAULT_MAX_PDF_SIZE_BYTES


def test_get_settings_reads_mongodb_config_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("MONGODB_URI", "mongodb://db:27017")
    monkeypatch.setenv("MONGODB_DB_NAME", "test-db")
    monkeypatch.setenv("MONGO_COLLECTION_NAME", "test-docs")

    settings = get_settings()

    assert settings.mongodb_uri == "mongodb://db:27017"
    assert settings.mongodb_db_name == "test-db"
    assert settings.mongodb_collection_name == "test-docs"


def test_get_settings_uses_mongodb_defaults(monkeypatch) -> None:
    for name in ("MONGODB_URI", "MONGODB_DB_NAME", "MONGO_COLLECTION_NAME"):
        monkeypatch.delenv(name, raising=False)

    settings = get_settings()

    assert settings.mongodb_uri == "mongodb://localhost:27017"
    assert settings.mongodb_db_name == "pdf-extractext"
    assert settings.mongodb_collection_name == "documents"


def test_settings_repr_hides_mongodb_uri(monkeypatch) -> None:
    monkeypatch.setenv("MONGODB_URI", "mongodb+srv://user:secreto@cluster")

    assert "secreto" not in repr(get_settings())


def test_get_settings_uses_info_log_level_by_default(monkeypatch) -> None:
    monkeypatch.delenv("APP_LOG_LEVEL", raising=False)

    assert get_settings().log_level == "INFO"


def test_get_settings_reads_log_level_case_insensitive(monkeypatch) -> None:
    monkeypatch.setenv("APP_LOG_LEVEL", "debug")

    assert get_settings().log_level == "DEBUG"


def test_get_settings_uses_default_for_invalid_log_level(monkeypatch) -> None:
    monkeypatch.setenv("APP_LOG_LEVEL", "verboso")

    assert get_settings().log_level == "INFO"


def test_settings_has_no_named_environment() -> None:
    assert not hasattr(get_settings(), "app_env")


def test_settings_has_no_app_version() -> None:
    assert not hasattr(get_settings(), "app_version")


def test_get_settings_uses_extract_service_defaults(monkeypatch) -> None:
    monkeypatch.delenv("EXTRACT_SERVICE_URL", raising=False)
    monkeypatch.delenv("EXTRACT_TIMEOUT_S", raising=False)

    settings = get_settings()

    assert settings.extract_service_url == DEFAULT_EXTRACT_SERVICE_URL
    assert settings.extract_timeout_s == DEFAULT_EXTRACT_TIMEOUT_S


def test_get_settings_reads_extract_service_config_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("EXTRACT_SERVICE_URL", "http://extract:8000")
    monkeypatch.setenv("EXTRACT_TIMEOUT_S", "12")

    settings = get_settings()

    assert settings.extract_service_url == "http://extract:8000"
    assert settings.extract_timeout_s == 12


def test_get_settings_uses_default_for_invalid_extract_timeout(monkeypatch) -> None:
    monkeypatch.setenv("EXTRACT_TIMEOUT_S", "nunca")

    assert get_settings().extract_timeout_s == DEFAULT_EXTRACT_TIMEOUT_S
