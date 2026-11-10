"""Preferencias locales de la interfaz de escritorio."""

import json
import os

from pathlib import Path
from urllib.parse import urlparse


def defaults():
    gateway = os.getenv(
        "API_URL",
        "http://127.0.0.1:8000",
    )

    return {
        "extract_url": os.getenv(
            "EXTRACT_API_URL",
            gateway,
        ),
        "documents_url": os.getenv(
            "DOCUMENTS_API_URL",
            gateway,
        ),
        "theme": "dark",
    }


def config_path():
    base = Path(os.getenv("APPDATA") or os.getenv("XDG_CONFIG_HOME") or Path.home() / ".config")

    return base / "pdf-extractext" / "settings.json"


def valid_url(value):
    try:
        parsed = urlparse(value)

        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.hostname)
            and parsed.port != 0
            and not parsed.username
            and not parsed.password
            and not parsed.query
            and not parsed.fragment
        )

    except ValueError:
        return False


def load_settings(path=None):
    settings = defaults()

    try:
        settings_file = path or config_path()

        content = settings_file.read_text(
            encoding="utf-8",
        )

        data = json.loads(content)

        if isinstance(data, dict):
            for key in (
                "extract_url",
                "documents_url",
            ):
                value = data.get(key)

                if isinstance(value, str) and valid_url(value):
                    settings[key] = value.rstrip("/")

            if data.get("theme") in (
                "dark",
                "light",
                "system",
            ):
                settings["theme"] = data["theme"]

    except OSError, ValueError, TypeError:
        pass

    return settings


def save_settings(settings, path=None):
    urls_are_valid = all(
        valid_url(settings.get(key, ""))
        for key in (
            "extract_url",
            "documents_url",
        )
    )

    if not urls_are_valid:
        raise ValueError("Ingresá URL válidas que comiencen " "con http:// o https://.")

    if settings.get("theme") not in (
        "dark",
        "light",
        "system",
    ):
        raise ValueError("Seleccioná un tema válido.")

    target = path or config_path()

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    content = json.dumps(
        settings,
        ensure_ascii=False,
        indent=2,
    )

    target.write_text(
        content,
        encoding="utf-8",
    )
