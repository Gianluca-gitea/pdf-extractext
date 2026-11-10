import httpx
from pymongo import timeout
from pymongo.errors import PyMongoError

from app.models import HealthStatus
from app.repositories.document_repository import get_document_repository
from app.services.extract_client import get_extract_client


def dependencies_ready() -> bool:
    try:
        with timeout(2.0):
            get_document_repository().client.admin.command("ping")
        response = get_extract_client().get("/ready", timeout=2.0)
        return (
            response.status_code == 200
            and HealthStatus.model_validate(response.json()).status == "ok"
        )
    except PyMongoError, httpx.HTTPError, ValueError:
        return False
