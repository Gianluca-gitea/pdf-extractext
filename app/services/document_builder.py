from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def construir_documento(
    pdf_nombre: str,
    texto_extraido: str,
    checksum_archivo: str,
    duracion_ms: int,
    estado: str = "ok",
    error: str | None = None,
) -> dict:

    logger.debug(
        "Building document dict: pdf_nombre=%s checksum=%s text_chars=%d status=%s",
        pdf_nombre,
        checksum_archivo,
        len(texto_extraido),
        estado
    )

    return {
        "pdf_nombre": pdf_nombre,
        "txt_contenido": texto_extraido,
        "txt_chars": len(texto_extraido),
        "checksum_archivo": checksum_archivo,
        "checksum_algoritmo": "sha256",
        "estado": estado,
        "error": error,
        "created_at": datetime.now(timezone.utc),
        "duracion_ms": duracion_ms,
    }
