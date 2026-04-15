from app.settings import get_settings


def test_get_settings_reads_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "PDF Extractext Test")
    monkeypatch.setenv("APP_VERSION", "9.9.9")
    monkeypatch.setenv("APP_ENV", "test")

    settings = get_settings()

    assert settings.app_name == "PDF Extractext Test"
    assert settings.app_version == "9.9.9"
    assert settings.app_env == "test"
