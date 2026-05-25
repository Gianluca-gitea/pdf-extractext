from __future__ import annotations

import logging

from bson.objectid import ObjectId

from app.repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ALLOWED_ESTADOS = {"pendiente", "ok", "error"}
ALLOWED_ESTADO_TRANSITIONS = {
    None: {"pendiente", "ok", "error"},
    "pendiente": {"ok", "error"},
    "error": {"pendiente"},
    "ok": set(),
}


class InvalidStatusTransitionError(ValueError):
    pass


class DocumentService:
    def __init__(self, repository: DocumentRepository | None = None) -> None:
        self.repository = repository or DocumentRepository()

    def list_documents(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        include_text: bool = False,
    ) -> list[dict]:
        return self.repository.list_documents(skip=skip, limit=limit, include_text=include_text)

    def get_document_by_id(self, document_id: ObjectId, include_text: bool = True) -> dict | None:
        return self.repository.find_by_id(document_id, include_text=include_text)

    def get_document_by_checksum(self, checksum: str) -> dict | None:
        return self.repository.find_by_checksum(checksum)

    def update_document(self, document_id: ObjectId, updates: dict) -> dict | None:
        existing = self.repository.find_by_id(document_id, include_text=False)
        if existing is None:
            return None

        if "estado" in updates:
            self._validate_status_transition(existing.get("estado"), updates["estado"])

        return self.repository.update_document(document_id, updates)

    def delete_document(self, document_id: ObjectId) -> bool:
        return self.repository.delete_document(document_id)

    def _validate_status_transition(self, current_estado: str | None, new_estado: str) -> None:
        if new_estado not in ALLOWED_ESTADOS:
            raise InvalidStatusTransitionError(f"Estado invalido: {new_estado}")

        if current_estado == new_estado:
            return

        allowed = ALLOWED_ESTADO_TRANSITIONS.get(current_estado, ALLOWED_ESTADOS)
        if new_estado not in allowed:
            raise InvalidStatusTransitionError(
                f"Transicion de estado invalida: {current_estado} -> {new_estado}"
            )
