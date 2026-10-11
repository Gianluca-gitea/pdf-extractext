from importlib.metadata import version

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_version_comes_from_package_metadata() -> None:
    assert app.version == version("pdf-extractext-api")
