"""Cliente HTTP para los servicios de PDF Extractext."""

from pathlib import Path

import requests


class ApiError(Exception):
    """Error que se puede mostrar al usuario en la interfaz."""


class ApiClient:

    def __init__(
        self,
        extract_url,
        documents_url,
        timeout=120,
        session=None,
    ):
        self.extract_url = extract_url.rstrip("/")
        self.documents_url = documents_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def _request(self, method, url, **kwargs):
        try:
            response = self.session.request(
                method,
                url,
                timeout=(5, self.timeout),
                **kwargs,
            )

        except requests.Timeout as exc:
            raise ApiError(
                "El servidor tardó demasiado en responder. " "Intentá nuevamente."
            ) from exc

        except requests.ConnectionError as exc:
            raise ApiError(
                "No se pudo conectar al servidor. "
                "Comprobá que el backend esté iniciado y "
                "revisá las URL en Configuración."
            ) from exc

        except requests.RequestException as exc:
            raise ApiError(f"Error de comunicación: {exc}") from exc

        if not response.ok:
            try:
                detail = response.json().get("detail", "")

            except ValueError, AttributeError:
                detail = ""

            if not isinstance(detail, str):
                detail = str(detail)

            messages = {
                413: "El archivo supera el tamaño permitido.",
                503: ("El servicio está saturado. " "Intentá nuevamente en unos segundos."),
                504: "La extracción tardó demasiado.",
            }

            default_message = f"El servidor respondió con error " f"{response.status_code}."

            raise ApiError(
                detail
                or messages.get(
                    response.status_code,
                    default_message,
                )
            )

        try:
            return response.json()

        except ValueError as exc:
            raise ApiError("El servidor devolvió una respuesta inválida.") from exc

    def extract(self, path, output_format):
        path = Path(path)

        if output_format not in ("txt", "md"):
            raise ValueError("Formato de extracción inválido.")

        if output_format == "txt":
            url = self.documents_url + "/documents/upload"

            key = "extracted_text"

        else:
            url = self.extract_url + "/extract"
            key = "content"

        try:
            with path.open("rb") as pdf:
                files = {
                    "file": (
                        path.name,
                        pdf,
                        "application/pdf",
                    )
                }

                data = self._request(
                    "POST",
                    url,
                    files=files,
                )

        except OSError as exc:
            raise ApiError(f"No se pudo leer el archivo: {exc}") from exc

        if not isinstance(data, dict) or not isinstance(data.get(key), str):
            raise ApiError("El servidor no devolvió texto " "en el formato esperado.")

        return data[key]

    def history(self, skip=0, limit=20):
        data = self._request(
            "GET",
            self.documents_url + "/documents",
            params={
                "skip": skip,
                "limit": limit,
            },
        )

        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            raise ApiError("El servidor devolvió un historial inválido.")

        return data["items"]

    def document(self, doc_id):
        data = self._request(
            "GET",
            f"{self.documents_url}/documents/{doc_id}",
            params={
                "include_text": "true",
            },
        )

        if isinstance(data, dict):
            document = data.get("document")
        else:
            document = None

        if not isinstance(document, dict) or not isinstance(
            document.get("txt_contenido"),
            str,
        ):
            raise ApiError("El servidor devolvió un documento inválido.")

        return document

    def rename(self, doc_id, name):
        return self._request(
            "PATCH",
            f"{self.documents_url}/documents/{doc_id}",
            json={
                "pdf_nombre": name,
            },
        )

    def delete(self, doc_id):
        return self._request(
            "DELETE",
            f"{self.documents_url}/documents/{doc_id}",
        )
