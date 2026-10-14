from dataclasses import replace

import httpx
import pytest

from app.services import extract_client as extract_client_module
from app.services.extract_client import (
    ExtractServiceBusyError,
    ExtractServiceTimeoutError,
    ExtractServiceUnavailableError,
    InvalidPDFError,
    close_extract_client,
    extract_text,
    get_extract_client,
)
from app.settings import get_settings


def _client(handler) -> httpx.Client:
    return httpx.Client(base_url="http://extract", transport=httpx.MockTransport(handler))


def test_extract_text_posts_raw_pdf_and_returns_content() -> None:
    received = {}

    def handler(request: httpx.Request) -> httpx.Response:
        received["method"] = request.method
        received["path"] = request.url.path
        received["content_type"] = request.headers["content-type"]
        received["body"] = request.content
        return httpx.Response(200, json={"content": "texto plano", "page_count": 3})

    result = extract_text(b"%PDF-1.4 data", client=_client(handler))

    assert result == "texto plano"
    assert received == {
        "method": "POST",
        "path": "/extract/text",
        "content_type": "application/pdf",
        "body": b"%PDF-1.4 data",
    }


def test_extract_text_raises_invalid_pdf_with_detail_from_extract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"detail": "El contenido no corresponde a un PDF valido."})

    with pytest.raises(InvalidPDFError, match="El contenido no corresponde a un PDF valido."):
        extract_text(b"basura", client=_client(handler))


def test_extract_text_raises_busy_with_retry_after() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, headers={"Retry-After": "3"}, json={"detail": "saturado"})

    with pytest.raises(ExtractServiceBusyError) as exc_info:
        extract_text(b"%PDF-1.4", client=_client(handler))

    assert exc_info.value.retry_after == "3"


def test_extract_text_defaults_retry_after_to_one_second() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    with pytest.raises(ExtractServiceBusyError) as exc_info:
        extract_text(b"%PDF-1.4", client=_client(handler))

    assert exc_info.value.retry_after == "1"


def test_extract_text_raises_timeout_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("sin respuesta", request=request)

    with pytest.raises(ExtractServiceTimeoutError):
        extract_text(b"%PDF-1.4", client=_client(handler))


def test_extract_text_raises_unavailable_when_connection_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexión rechazada", request=request)

    with pytest.raises(ExtractServiceUnavailableError) as exc_info:
        extract_text(b"%PDF-1.4", client=_client(handler))

    assert not isinstance(exc_info.value, ExtractServiceTimeoutError)


@pytest.mark.parametrize("status_code", [413, 500, 502])
def test_extract_text_raises_unavailable_for_unexpected_status(status_code) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text="error")

    with pytest.raises(ExtractServiceUnavailableError, match=str(status_code)):
        extract_text(b"%PDF-1.4", client=_client(handler))


def test_get_extract_client_uses_settings_and_is_shared(monkeypatch) -> None:
    custom = replace(get_settings(), extract_service_url="http://extract:9000", extract_timeout_s=7)
    monkeypatch.setattr(extract_client_module, "get_settings", lambda: custom)
    close_extract_client()

    try:
        first = get_extract_client()
        second = get_extract_client()

        assert first is second
        assert str(first.base_url) == "http://extract:9000"
        assert first.timeout.read == 7
    finally:
        close_extract_client()

    assert get_extract_client.cache_info().currsize == 0


def test_close_extract_client_does_nothing_when_not_started() -> None:
    close_extract_client()
    close_extract_client()

    assert get_extract_client.cache_info().currsize == 0
