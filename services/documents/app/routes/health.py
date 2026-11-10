from app.models import HealthStatus
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.services.health_service import dependencies_ready

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
@router.get("/health/live", response_model=HealthStatus)
def liveness():
    return {"status": "ok"}


@router.get("/ready", response_model=HealthStatus)
def readiness():
    if not dependencies_ready():
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok"}
