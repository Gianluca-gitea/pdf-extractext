from datetime import datetime
from typing import Any, Literal
from bson.objectid import ObjectId
from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

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

    @model_validator(mode="before")
    @classmethod
    def _convert_from_mongo(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        converted = dict(data)
        doc_id = converted.get("_id")
        if isinstance(doc_id, ObjectId):
            converted["_id"] = str(doc_id)
        for field in ("created_at", "deleted_at"):
            val = converted.get(field)
            if isinstance(val, datetime):
                converted[field] = val.isoformat()
        return converted


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


class DocumentBuilt(BaseModel):
    """Contrato interno tipado para el documento construido por document_builder.

    No incluye _id (lo genera Mongo al insertar). Usado como frontera entre
    document_builder → upload_service → document_repository.
    """

    pdf_nombre: str
    txt_contenido: str
    txt_chars: int = Field(ge=0)
    checksum_archivo: str
    checksum_algoritmo: str = "sha256"
    estado: Literal["pendiente", "ok", "error"] = "pendiente"
    error: str | None = Field(default=None, max_length=500)
    created_at: datetime
    deleted_at: datetime | None = None
    duracion_ms: int = Field(ge=0)


class ProcessedUploadResult(BaseModel):
    """Contrato de respuesta de upload_service.process_pdf_upload."""

    document_id: str
    document: DocumentBuilt
