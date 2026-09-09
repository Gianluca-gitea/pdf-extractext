# Auditoría de Correcciones — PDF Extractext

Auditoría de todo el proyecto buscando infracciones de principios de **DRY, KISS, YAGNI, 12-Factor App, SOLID, lógica de negocio**, etc. Cada hallazgo incluye **Archivo**, **Severidad** y **Corrección sugerida**.

> **Revisión 2026-09-09:** verificados los puntos **1, 3 y 4** — aprobados y eliminados (config centralizada en `Settings` con inyección en `DocumentRepository`; `load_dotenv()` movido a `run_dev.py`). La numeración original se conserva.
> **Revisión 2026-09-09 (2):** punto **2** aprobado y eliminado — fail-fast real en `get_settings()` (`MONGODB_URI` obligatoria fuera de `dev`/`test`); el repositorio vuelve a fuente única sin `os.getenv`.
> **Revisión 2026-09-09 (3):** punto **7** aprobado y eliminado — serialización genérica en `app/services/serializers.py` (`serialize_value`/`serialize_document`, primer nivel) usada por los 5 sitios de `app/main.py`, con `tests/test_serializers.py`.
> **Revisión 2026-09-09 (4):** punto **9** aprobado y eliminado — `DocumentoEstado` (`Literal["pendiente","ok","error"]`) en `app/services/document_status.py`; usado en `document_service.py` (`ALLOWED_ESTADOS`), `document_builder.py` (firma tipada), `main.py` (`DocumentUpdate.estado`), `pdf_service.py` (import para coherencia).

---

## Configuración y Entorno (12-Factor App)

### 5. Versiones de Python/objetivos inconsistentes en `pyproject.toml`
- **Archivos:** `pyproject.toml`, `Dockerfile`
- **Severidad:** Baja
- **Descripción:** `requires-python = ">=3.14"` y el Dockerfile usan `python:3.14`, pero `[tool.black]`, `[tool.ruff]` y `[tool.mypy]` usan `target-version`/`python_version = "3.12"`. Inconsistencia entre el objetivo de ejecución y el de tooling.
- **Corrección:** Unificar todos en 3.14 (o el mínimo soportado real) para evitar que el linting no detecte código incompatible con el runtime.
- **Estado (revisión 2026-09-09, parcial):** `[tool.black]` unificado a `py314` (verificado con black 26.3.1) y `select` de ruff migrado a `[tool.ruff.lint]` (fin del warning deprecado). Pendiente: `[tool.ruff]` sigue en `py312` y `[tool.mypy]` en `3.12` porque los pins `ruff==0.3.0` y `mypy==1.8.0` no aceptan 3.14 — requiere alcance completo (subir pins + `uv lock`).

### 6. Dependencias duplicadas e inconsistentes en `pyproject.toml`
- **Archivos:** `pyproject.toml:22-29` y `pyproject.toml:91-96`
- **Severidad:** Media
- **Descripción:** Existen **dos** grupos de dependencias dev: `[project.optional-dependencies].dev` y `[dependency-groups].dev`. Además:
  - `pytest==9.0.3` aparece en ambos.
  - El grupo `[dependency-groups].dev` declara `httpx2>=0.28.0`, un paquete **inexistente** (el real es `httpx`). Esto es un bug latente.
  - `pytest-mock` se usa en los tests (`mocker`) pero solo está en `[dependency-groups]`, no en optional-dependencies.
- **Corrección:** Consolidar en un único lugar (recomendado: `[dependency-groups]` de uv) y corregir `httpx2` → `httpx`. Eliminar duplicación.

---

## DRY (Duplicación de código)

### 8. Lógica de "Documento no encontrado" repetida en cada endpoint (`app/main.py`)
- **Archivo:** `app/main.py`
- **Severidad:** Media (DRY)
- **Descripción:** Los bloques `if document is None: ... raise HTTPException(404, "Documento no encontrado.")` se repiten en 4 endpoints (`by-checksum`, `get_by_id`, `update`, `download`).
- **Corrección:** Extraer un helper `_get_or_404` o un `@app.get` utilitario que centralice el manejo y el logging del 404.

### 10. Repetición del patrón `seleccion == []` y `tree.item(...)['values'][0]` en `app/interface.py`
- **Archivo:** `app/interface.py`
- **Severidad:** Baja (DRY)
- **Descripción:** `ver_texto_historial`, `renombrar_historial` y `eliminar_historial` repiten la misma extracción de "selección seleccionada" y el warning "Seleccioná un documento de la lista."
- **Corrección:** Extraer un helper `_get_selected_document(tree) -> str | None`.

### 11. Endpoint `by-checksum` y `get_by_id` con forma de respuesta idéntica (`app/main.py`)
- **Archivo:** `app/main.py:82-132`
- **Severidad:** Baja (DRY)
- **Descripción:** Ambos devuelven `{"document_id": ..., "document": ...}` y comparten el patrón 404. Se pueden unificar mediante un endpoint genérico o un serializer común.

---

## KISS / YAGNI

### 12. `_model_dump` con soporte legacy (`app/main.py:68-71`)
- **Archivo:** `app/main.py`
- **Severidad:** Baja (YAGNI/KISS)
- **Descripción:** `_model_dump` contempla la API antigua `model.dict(exclude_unset=True)` "por si acaso". Con pydantic v2 moderno y el `requires-python >=3.14`/FastAPI >=0.120 es código muerto.
- **Corrección:** Usar directamente `payload.model_dump(exclude_unset=True)` y eliminar el helper.

### 13. Código muerto / comentado en `app/services/pdf_service.py:122-130, 160-161, 175-176`
- **Archivo:** `app/services/pdf_service.py`
- **Severidad:** Media (YAGNI)
- **Descripción:** `_save_text_to_disk` está definida pero **nunca se llama** (solo hay llamadas comentadas). Además `TEXT_BLOCK`/`IMAGE_BLOCK` como constantes de módulo no aportan mucho.
- **Corrección:** Eliminar `_save_text_to_disk` y los bloques comentados si no se va a reactivar la funcionalidad. El código comentado no debe quedar en el repo.

### 14. `duracion_ms` y `checksum_algoritmo` "fijos" (`app/services/document_builder.py`)
- **Archivo:** `app/services/document_builder.py`
- **Severidad:** Baja (KISS)
- **Descripción:** `checksum_algoritmo` siempre es `"sha256"`. Si solo existe una implementación, es redundante persistir el algoritmo (YAGNI); si se quiere extensible, debería venir del servicio de checksum.
- **Corrección:** Decidir: eliminarlo o derivarlo de `checksum_service`.

### 15. Interfaz con URL hardcodeada repetida (`app/interface.py`)
- **Archivo:** `app/interface.py`
- **Severidad:** Media (DRY/12-Factor)
- **Descripción:** `http://127.0.0.1:8000` aparece hardcodeado en 5+ lugares (`extraer_texto`, `cargar_lista_historial`, `ver_texto_historial`, `renombrar_historial`, `eliminar_historial`). Violación de 12-Factor (config) y DRY.
- **Corrección:** Definir `API_BASE_URL` en una constante o en `settings`, y construir las URLs a partir de ella.

---

## SOLID

### 16. Inversión de dependencias incompleta en `app/services/document_service.py:27` y `pdf_service.py:148`
- **Archivo:** `app/services/document_service.py:27`, `app/services/pdf_service.py:148`
- **Severidad:** Media (DIP/SRP)
- **Descripción:** Aunque `DocumentService` y `process_pdf_upload` aceptan un repository inyectable, en los endpoints `main.py` siempre se instancia `DocumentService()` sin parámetros, que crea `DocumentRepository()` internamente (con `os.getenv` y conexión real). La capa HTTP está acoplada al constructor concreto y dificulta el testeo y el manejo de la conexión.
- **Corrección:** Usar un mecanismo de inyección de dependencias (FastAPI `Depends`) para construir `DocumentService`/`DocumentRepository` una sola vez (compartir `MongoClient`) y pasarlos a los endpoints.

### 17. Ningún endpoint recibe dependencias (`app/main.py`)
- **Archivo:** `app/main.py`
- **Severidad:** Media (SOLID)
- **Descripción:** Cada endpoint hace `service = DocumentService()` creando una **nueva conexión Mongo** por request. Desperdicia recursos y complica el control de ciclo de vida.
- **Corrección:** Mantener un único `MongoClient`/`DocumentService` por aplicación e inyectarlo como dependencia.

### 18. `interface.py` viola SRP y es acoplado
- **Archivo:** `app/interface.py`
- **Severidad:** Baja (SRP)
- **Descripción:** El archivo mezcla construcción de UI, llamadas HTTP y lógica de negocio en funciones sueltas con estado global (`archivo_pdf`, `texto_extraido_global`). Además la UI **crea `tk.Tk()` al importar el módulo** (líneas 340-441), lo que impide importar funciones sin lanzar una ventana.
- **Corrección:** Separar cliente HTTP (repositorio/API client), lógica de negocio y capa de presentación; mover la creación de `tk.Tk()` bajo `if __name__ == "__main__"`.

### 19. `interface.py` acopla a un backend concreto de requests (`app/interface.py`)
- **Archivo:** `app/interface.py`
- **Severidad:** Baja (DIP)
- **Descripción:** La capa de presentación depende directamente de `requests` y de la serialización JSON del backend. Un cambio de API rompe la UI.
- **Corrección:** Introducir un pequeño "client API" desacoplado (inyectable) que abstraiga upload/list/get/patch/delete.

---

## Lógica de Negocio / Bugs

### 20. Bug: borrar un documento con texto en memoria no limpia `texto_extraido_global` (`app/interface.py`)
- **Archivo:** `app/interface.py`
- **Severidad:** Media (lógica de negocio/UX)
- **Descripción:** Tras eliminar un documento del historial, el texto sigue visible en `texto_resultado`, dejando la UI en un estado inconsistente (muestra texto de un documento borrado).
- **Corrección:** Tras `eliminar_historial`, limpiar `texto_extraido_global` y el `Text` si corresponde.

### 21. Bug: `descargar_txt` descarga lo que esté en memoria, no el documento del historial (`app/interface.py`)
- **Archivo:** `app/interface.py:93-127`
- **Severidad:** Baja (lógica de negocio)
- **Descripción:** El botón "Descargar TXT" siempre guarda `texto_extraido_global` (lo último cargado), no el documento seleccionado. Comportamiento confuso si el usuario selecciona un documento y descarga otro.
- **Corrección:** Vincular la descarga al documento activo o dejar explícito que descarga la última selección.

### 22. Bug: `update_document` en `main.py` filtra campos `None` de forma frágil (`app/main.py:140-145`)
- **Archivo:** `app/main.py`
- **Severidad:** Media (lógica de negocio)
- **Descripción:** `updates = _model_dump(payload)` con `exclude_unset=True` solo incluye campos enviados. Luego el código vuelve a hacer `if updates.get("pdf_nombre") is None: updates.pop(...)` — redundante y potencialmente borra un valor legítimo `None`. La limpieza es innecesaria porque `exclude_unset=True` ya excluye los no enviados.
- **Corrección:** Eliminar el bloque de limpieza; `exclude_unset=True` ya resuelve el caso.

### 23. Bug: validación de estado ocurre tras la comprobación de existencia pero sin transacción (`app/services/document_service.py:44-52`)
- **Archivo:** `app/services/document_service.py`
- **Severidad:** Baja (lógica de negocio)
- **Descripción:** `find_by_id` (lectura) y `update_document` (escritura) son operaciones separadas: una race condition entre ambas puede causar una transición de estado inválida aplicada a ciegas o sobrescribir otros campos.
- **Corrección:** Si la consistencia es crítica, hacer la validación+update atómicamente (p. ej. con el estado leído dentro de la condición del `find_one_and_update`).

### 24. Bug: `include_text` en `GET /documents/by-checksum` siempre devuelve todo el texto (`app/repositories/document_repository.py:70-73`)
- **Archivo:** `app/repositories/document_repository.py`
- **Severidad:** Baja (lógica de negocio)
- **Descripción:** `find_by_checksum` no recibe `include_text`, así que `by-checksum` expone siempre el contenido completo del `txt_contenido` (documento de máximo 5 MB), potenciamente pesado e innecesario si el cliente solo quiere el ID.
- **Corrección:** Aceptar `include_text` en `find_by_checksum` y en el endpoint, como ya existe en `find_by_id`.

### 25. `estado="ok"` se hardcodea en `process_pdf_upload` (`app/services/pdf_service.py:185`)
- **Archivo:** `app/services/pdf_service.py`
- **Severidad:** Baja (lógica de negocio)
- **Descripción:** Aunque `construir_documento` define un estado por defecto `"pendiente"`, `process_pdf_upload` fuerza `"ok"` aunque la extracción esté vacía (p. ej. por OCR fallido). Un documento sin texto se marca como "ok".
- **Corrección:** Decidir y aplicar una regla clara: si la extracción devuelve texto vacío, el estado debería ser `error` o `pendiente`, no `ok`.

### 26. Consistencia: `extracted_text` se re-extrae de `file_bytes` mientras `file` completo también se tiene en la interfaz (`app/interface.py:47-60`)
- **Archivo:** `app/interface.py`, `app/services/pdf_service.py`
- **Severidad:** Baja (lógica de negocio)
- **Descripción:** La UI envía el archivo completo con nombre fijo `"archivo.pdf"` (ignora el nombre real del PDF seleccionado). El backend guarda `pdf_nombre = file_name` que siempre será `"archivo.pdf"`, perdiendo el nombre original del archivo.
- **Corrección:** Enviar el nombre real (`os.path.basename(archivo_pdf)`) en el campo `filename` del multipart.

---

## Robustez / Manejo de Errores

### 27. `except Exception` silencioso en OCR (`app/services/pdf_service.py:59-65`)
- **Archivo:** `app/services/pdf_service.py`
- **Severidad:** Media
- **Descripción:** Cualquier error en `pytesseract.image_to_string` se traga y devuelve `""`, ocultando fallos reales de OCR y produciendo documentos "ok" sin texto.
- **Corrección:** Propagar o registrar con nivel de error y marcar el documento como `error` (ver punto 25).

### 28. `except Exception` en `_parse_document_id` (`app/main.py:76`)
- **Archivo:** `app/main.py`
- **Severidad:** Baja
- **Descripción:** Captura `Exception` genérica al construir el `ObjectId`. Debería capturar la excepción específica (`bson.errors.InvalidId`).
- **Corrección:** Capturar `InvalidId` de `bson.errors`.

### 29. Falta validación/tamaño de `DocumentUpdate.error` con lógica de negocio (`app/main.py:43`)
- **Archivo:** `app/main.py`
- **Severidad:** Baja
- **Descripción:** El campo `error` del esquema puede actualizarse libremente sin asociarse a un estado `error`. Los estados y los mensajes de error deberían estar ligados para mantener coherencia de negocio.
- **Corrección:** Regla de negocio: `error` solo debería permitirse cuando `estado == "error"`.

---

## Tests / Mantenibilidad

### 30. Tests acoplados a la creación de `tk.Tk()` (`tests/test_interface.py`)
- **Archivo:** `app/interface.py`, `tests/test_interface.py`
- **Severidad:** Media
- **Descripción:** `import app.interface` ejecuta `tk.Tk()` a nivel de módulo. Los tests lo "funcionan" porque en CI suele fallar sin display. Al mover la UI al `__main__` (punto 18), los tests deberían refactorizarse para no depender de instanciar la ventana.
- **Corrección:** Refactorizar `interface.py` para que importar no cree la ventana, y ajustar los tests.

### 31. Tests sin `__init__.py` ni estructura que aísle config (`tests/`)
- **Archivo:** `tests/*.py`
- **Severidad:** Baja
- **Descripción:** Los tests de `main` crean `TestClient(app)` a nivel de módulo e instancian `DocumentService()` con conexión real en cada endpoint (revisión 2026-09-09: `main` ya no carga `.env`, ese acoplamiento quedó resuelto). Deberían aislar por completo la persistencia para ser deterministas.
- **Corrección:** Centralizar fixtures/mocks de repositorio y evitar conexiones reales a Mongo en unit tests.

---

## Resumen por severidad

- **Alta:** — (el punto 1 fue resuelto y eliminado)
- **Media:** 6, 8, 13, 15, 16, 17, 20, 22, 27, 30 (10 ítems)
- **Baja:** 5, 10, 11, 12, 14, 18, 19, 21, 23, 24, 25, 26, 28, 29, 31

**Prioridad de acción sugerida:**
1. Inyección de dependencias y ciclo de vida de Mongo (16, 17).
2. Refactorizar `interface.py` (desacople + URL + bug 20/21/22/26).
3. Limpiar código muerto y consolidar dependencias (6, 13, 12).
