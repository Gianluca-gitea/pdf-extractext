from typing import Literal
from pydantic import BaseModel, Field


class ExtractionResult(BaseModel):
    content: str = Field(strict=True)
    page_count: int = Field(ge=0, strict=True)


class HealthStatus(BaseModel):
    status: Literal["ok", "unavailable"]


class DocumentUpdate(BaseModel):
    pdf_nombre: str | None = Field(default=None, min_length=1, max_length=200)
    estado: Literal["pendiente", "ok", "error"] | None = None
    error: str | None = Field(default=None, max_length=500)


class PublicDocument(BaseModel):
    id: str = Field(alias="_id")
    pdf_nombre: str | None = None
    txt_contenido: str | None = None
    txt_chars: int | None = Field(default=None, ge=0)
    checksum_archivo: str | None = None
    checksum_algoritmo: str | None = None
    estado: Literal["pendiente", "ok", "error"] | None = None
    error: str | None = None
    created_at: str | None = None
    deleted_at: str | None = None
    duracion_ms: int | None = Field(default=None, ge=0)


class DocumentResponse(BaseModel):
    document_id: str
    document: PublicDocument


class DocumentList(BaseModel):
    items: list[PublicDocument]
    count: int = Field(ge=0)
    skip: int = Field(ge=0)
    limit: int = Field(ge=1)


class UploadResponse(BaseModel):
    filename: str
    content_type: str
    size_bytes: int = Field(ge=1)
    extracted_text: str
    status: Literal["uploaded"]


class DeleteResponse(BaseModel):
    status: Literal["deleted"]
