from app.models import HealthStatus
from fastapi import APIRouter

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
@router.get("/health/live", response_model=HealthStatus)
@router.get("/ready", response_model=HealthStatus)
def liveness():
    return {"status": "ok"}
