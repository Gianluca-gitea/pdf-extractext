from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.models import DocumentBuilt

logger = logging.getLogger(__name__)


def construir_documento(
    pdf_nombre: str,
    texto_extraido: str,
    checksum_archivo: str,
    duracion_ms: int,
    estado: str = "pendiente",
    error: str | None = None,
) -> DocumentBuilt:

    logger.debug(
        "Building document: pdf_nombre=%s checksum=%s text_chars=%d status=%s",
        pdf_nombre,
        checksum_archivo,
        len(texto_extraido),
        estado,
    )

    return DocumentBuilt(
        pdf_nombre=pdf_nombre,
        txt_contenido=texto_extraido,
        txt_chars=len(texto_extraido),
        checksum_archivo=checksum_archivo,
        estado=estado,
        error=error,
        created_at=datetime.now(timezone.utc),
        deleted_at=None,
        duracion_ms=duracion_ms,
    )
