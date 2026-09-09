"""Entrypoint explícito solo para desarrollo local.

Carga `.env` (12-Factor: únicamente como conveniencia local) y arranca uvicorn.
En Docker, CI o cloud la configuración debe venir del entorno real;
`app.main` nunca carga `.env` por sí mismo.
"""

from __future__ import annotations

import uvicorn
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
