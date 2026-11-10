from __future__ import annotations

import logging
from typing import Literal

from bson.objectid import ObjectId

from app.errors import InvalidStatusTransitionError as InvalidStatusTransitionError
from app.models import PublicDocument
from app.repositories.document_repository import DocumentRepository, get_document_repository

logger = logging.getLogger(__name__)

ALLOWED_ESTADOS: set[Literal["pendiente", "ok", "error"]] = {
    "pendiente",
    "ok",
    "error",
}
ALLOWED_ESTADO_TRANSITIONS: dict[Literal["pendiente", "ok", "error"] | None, set[Literal["pendiente", "ok", "error"]]] = {
    None: {"pendiente", "ok", "error"},
    "pendiente": {"ok", "error"},
    "error": {"pendiente"},
    "ok": set(),
}


class DocumentService:
    def __init__(self, repository: DocumentRepository | None = None) -> None:
        self.repository = repository or get_document_repository()

    def list_documents(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        include_text: bool = False,
    ) -> list[PublicDocument]:
        documents = self.repository.list_documents(
            skip=skip, limit=limit, include_text=include_text
        )
        return [PublicDocument.model_validate(doc) for doc in documents]

    def get_document_by_id(
        self, document_id: ObjectId, include_text: bool = True
    ) -> PublicDocument | None:
        document = self.repository.find_by_id(document_id, include_text=include_text)
        if document is None:
            return None
        return PublicDocument.model_validate(document)

    def get_document_by_checksum(self, checksum: str) -> PublicDocument | None:
        document = self.repository.find_by_checksum(checksum)
        if document is None:
            return None
        return PublicDocument.model_validate(document)

    def update_document(
        self, document_id: ObjectId, updates: dict
    ) -> PublicDocument | None:
        existing = self.repository.find_by_id(document_id, include_text=False)
        if existing is None:
            return None

        if "estado" in updates:
            self._validate_status_transition(
                existing.get("estado"), updates["estado"]  # type: ignore[arg-type]
            )

        updated = self.repository.update_document(document_id, updates)
        if updated is None:
            return None
        return PublicDocument.model_validate(updated)

    def delete_document(self, document_id: ObjectId) -> bool:
        return self.repository.delete_document(document_id)

    def _validate_status_transition(
        self,
        current_estado: Literal["pendiente", "ok", "error"] | None,
        new_estado: Literal["pendiente", "ok", "error"],
    ) -> None:
        if new_estado not in ALLOWED_ESTADOS:
            raise InvalidStatusTransitionError(f"Estado invalido: {new_estado}")

        if current_estado == new_estado:
            return

        allowed = ALLOWED_ESTADO_TRANSITIONS.get(current_estado, ALLOWED_ESTADOS)
        if new_estado not in allowed:
            raise InvalidStatusTransitionError(
                f"Transicion de estado invalida: {current_estado} -> {new_estado}"
            )
