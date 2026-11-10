from typing import Literal
from pydantic import BaseModel, Field


class ExtractionResult(BaseModel):
    content: str = Field(strict=True)
    page_count: int = Field(ge=0, strict=True)


class HealthStatus(BaseModel):
    status: Literal["ok", "unavailable"]
