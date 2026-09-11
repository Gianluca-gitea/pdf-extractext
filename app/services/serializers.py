"""Serialización genérica de documentos MongoDB para respuestas HTTP.

Convierte valores no JSON-serializables (`datetime`, `ObjectId`) de forma
genérica iterando el primer nivel del dict, sin lógica campo a campo.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from bson.objectid import ObjectId

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def serialize_value(value: Any) -> Any:
    """Convierte un valor a su representación JSON-compatible.

    - `datetime` -> ISO 8601 (`isoformat`).
    - `ObjectId` -> `str`.
    - Cualquier otro valor (incluido `None`) se devuelve intacto.
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, ObjectId):
        return str(value)
    return value


def serialize_document(document: dict) -> dict:
    """Devuelve una copia del documento con sus valores serializados.

    Solo recorre el primer nivel (los documentos guardados son planos).
    No muta el dict de entrada.
    """
    serialized = {key: serialize_value(value) for key, value in document.items()}
    logger.debug("Serialized document keys=%s", list(serialized.keys()))
    return serialized
