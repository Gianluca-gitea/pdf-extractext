import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app import main as main_module
from app.body_limit import BODY_TOO_LARGE_ERROR_TEMPLATE, BodySizeLimitMiddleware

MAX_BODY_BYTES = 10


@pytest.fixture
def calls() -> list[bytes]:
    return []


@pytest.fixture
def client(calls) -> TestClient:
    app = FastAPI()
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=MAX_BODY_BYTES)

    @app.post("/echo")
    async def echo(request: Request) -> dict[str, int]:
        body = await request.body()
        calls.append(body)
        return {"size": len(body)}

    return TestClient(app)


def _too_large() -> dict[str, str]:
    return {"detail": BODY_TOO_LARGE_ERROR_TEMPLATE.format(max_size=MAX_BODY_BYTES)}


def test_lets_body_within_limit_through(client, calls) -> None:
    response = client.post("/echo", content=b"x" * MAX_BODY_BYTES)

    assert response.status_code == 200
    assert calls == [b"x" * MAX_BODY_BYTES]


def test_rejects_declared_content_length_over_limit_without_calling_endpoint(client, calls) -> None:
    response = client.post("/echo", content=b"x" * (MAX_BODY_BYTES + 1))

    assert response.status_code == 413
    assert response.json() == _too_large()
    assert calls == []


def test_rejects_streamed_body_over_limit_without_content_length(client, calls) -> None:
    response = client.post("/echo", content=iter([b"x" * 6, b"x" * 6]))

    assert response.status_code == 413
    assert response.json() == _too_large()
    assert calls == []


def test_app_limits_body_to_max_pdf_size_plus_multipart_overhead() -> None:
    middleware = next(m for m in main_module.app.user_middleware if m.cls is BodySizeLimitMiddleware)

    assert middleware.kwargs == {
        "max_body_bytes": main_module.settings.max_pdf_size_bytes
        + main_module.MULTIPART_OVERHEAD_BYTES
    }
