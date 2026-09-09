"""Tipos compartidos para estados de documento.

Define el conjunto canónico de estados válidos y el alias de tipo
para type-checkers (pydantic, mypy) y runtime.
"""

from __future__ import annotations

from typing import Literal, get_args

DocumentoEstado = Literal["pendiente", "ok", "error"]
ESTADOS_VALIDOS = frozenset(get_args(DocumentoEstado))
