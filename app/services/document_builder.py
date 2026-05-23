from __future__ import annotations

from datetime import datetime, timezone


def construir_documento(
    pdf_nombre: str,
    texto_extraido: str,
    checksum_archivo: str,
    duracion_ms: int,
    estado: str = "ok",
    error: str | None = None,
) -> dict:
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
