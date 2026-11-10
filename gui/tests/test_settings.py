"""Pruebas de la configuración de la interfaz."""

import pytest

from app_settings import (
    load_settings,
    save_settings,
    valid_url,
)


def test_valores_iniciales_usan_variables_de_entorno(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv(
        "API_URL",
        "http://gateway:8000",
    )

    monkeypatch.setenv(
        "EXTRACT_API_URL",
        "http://extract:8001",
    )

    monkeypatch.delenv(
        "DOCUMENTS_API_URL",
        raising=False,
    )

    configuracion = load_settings(tmp_path / "archivo_que_no_existe.json")

    assert configuracion["extract_url"] == "http://extract:8001"

    assert configuracion["documents_url"] == "http://gateway:8000"


def test_guardar_y_cargar_configuracion(tmp_path):
    archivo = tmp_path / "settings.json"

    esperado = {
        "extract_url": "http://localhost:8001",
        "documents_url": "http://localhost:8002",
        "theme": "light",
    }

    save_settings(
        esperado,
        archivo,
    )

    assert load_settings(archivo) == esperado


def test_archivo_danado_usa_valores_predeterminados(
    tmp_path,
):
    archivo = tmp_path / "settings.json"

    archivo.write_text(
        "{contenido invalido",
        encoding="utf-8",
    )

    configuracion = load_settings(archivo)

    assert configuracion["theme"] == "dark"


@pytest.mark.parametrize(
    "url",
    [
        "incorrecto",
        "ftp://servidor",
        "http://",
        "http://servidor:abc",
        "http://usuario:clave@servidor",
        "http://servidor?consulta=1",
    ],
)
def test_rechaza_url_invalidas(url):
    assert not valid_url(url)


def test_no_guarda_una_url_invalida(tmp_path):
    configuracion = {
        "extract_url": "incorrecto",
        "documents_url": "http://localhost",
        "theme": "dark",
    }

    with pytest.raises(ValueError):
        save_settings(
            configuracion,
            tmp_path / "settings.json",
        )
