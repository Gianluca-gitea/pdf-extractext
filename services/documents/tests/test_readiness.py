from datetime import datetime, timezone
from unittest.mock import MagicMock

import httpx
import pytest
from pymongo.errors import ConnectionFailure
from fastapi.testclient import TestClient
from app.main import app
from app.models import DocumentBuilt, ProcessedUploadResult
from app.services import health_service


@pytest.mark.parametrize("failure", ["mongo", "connection", "timeout", "status", "payload"])
def test_readiness_fails_and_recovers(monkeypatch, failure):
    repository = MagicMock()
    client = MagicMock()
    client.get.return_value = httpx.Response(200, json={"status": "ok"})
    monkeypatch.setattr(health_service, "get_document_repository", lambda: repository)
    monkeypatch.setattr(health_service, "get_extract_client", lambda: client)
    if failure == "mongo":
        repository.client.admin.command.side_effect = ConnectionFailure("offline")
    elif failure == "connection":
        client.get.side_effect = httpx.ConnectError("offline")
    elif failure == "timeout":
        client.get.side_effect = httpx.ReadTimeout("slow")
    elif failure == "status":
        client.get.return_value = httpx.Response(503)
    else:
        client.get.return_value = httpx.Response(200, json={"status": "down"})
    api = TestClient(app)
    assert api.get("/ready").status_code == 503
    assert api.get("/health/live").json() == {"status": "ok"}
    repository.client.admin.command.side_effect = None
    client.get.side_effect = None
    client.get.return_value = httpx.Response(200, json={"status": "ok"})
    assert api.get("/ready").status_code == 200
    repository.client.admin.command.assert_called_with("ping")
    client.get.assert_called_with("/ready", timeout=2.0)


def test_database_outage_returns_503(monkeypatch):
    from pymongo.errors import ConnectionFailure
    from app.routes import documents

    service = MagicMock()
    service.list_documents.side_effect = ConnectionFailure("private connection details")
    monkeypatch.setattr(documents, "DocumentService", lambda: service)
    response = TestClient(app).get("/documents")
    assert response.status_code == 503
    assert "private" not in response.text


def test_upload_recovers_without_another_readiness_check(monkeypatch):
    from app.routes import health, upload

    processor = MagicMock(
        return_value=ProcessedUploadResult(
            document_id="test",
            document=DocumentBuilt(
                pdf_nombre="test.pdf",
                txt_contenido="text",
                txt_chars=4,
                checksum_archivo="abc",
                estado="ok",
                error=None,
                created_at=datetime.now(timezone.utc),
                deleted_at=None,
                duracion_ms=0,
            ),
        )
    )
    monkeypatch.setattr(upload, "process_pdf_upload", processor)
    monkeypatch.setattr(health, "dependencies_ready", lambda: False)
    api = TestClient(app)
    assert api.get("/ready").status_code == 503
    # The dependencies recovered before this upload; no new readiness probe ran.
    payload = {"file": ("test.pdf", b"%PDF-1.4", "application/pdf")}
    assert api.post("/documents/upload", files=payload).status_code == 200
    processor.assert_called_once()
