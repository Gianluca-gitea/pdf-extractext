from app.settings import DEFAULT_MAX_PDF_SIZE_BYTES, get_settings


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
