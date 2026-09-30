# Auditoría de Correcciones — PDF Extractext

> **Estado actual (2026-09-30):** Ítems **1, 2, 3, 4, 7, 8, 9, 10** completados y verificados. Este documento contiene **solo lo pendiente**, ordenado por prioridad de ejecución.

---

## 🔴 PRIORIDAD ALTA — Base arquitectónica

### 16. Inyección de dependencias incompleta (DIP/SRP)
- **Archivos:** `app/main.py`, `app/services/document_service.py:27`, `app/services/pdf_service.py:148`, `app/repositories/document_repository.py:16-28`
- **Severidad:** Media
- **Descripción:** `DocumentService` y `DocumentRepository` aceptan dependencias inyectables, pero los endpoints instancian `DocumentService()` sin parámetros, creando nueva conexión Mongo por request.
- **Corrección:** Implementar `Depends(get_document_service)` con `MongoClient` singleton compartido. Factory que construya `DocumentRepository(mongo_client=shared_client)` e inyecte en `DocumentService`.

### 17. Ningún endpoint recibe dependencias (SOLID)
- **Archivo:** `app/main.py`
- **Severidad:** Media
- **Descripción:** Cada endpoint hace `service = DocumentService()` → nueva conexión Mongo por request.
- **Corrección:** Un único `MongoClient`/`DocumentService` por aplicación inyectado vía `Depends`. Resolver junto con punto 16.

---

## 🔴 PRIORIDAD ALTA — Refactor `interface.py` (desacople + bugs)

### 15. URL hardcodeada repetida (DRY/12-Factor)
- **Archivo:** `app/interface.py` (líneas 58, 135, 175, 222, 250)
- **Severidad:** Media
- **Descripción:** `http://127.0.0.1:8000` en 5+ lugares.
- **Corrección:** Constante `API_BASE_URL` (desde `settings` o env var) + builder de URLs.

### 18. `interface.py` viola SRP y crea `tk.Tk()` al importar (SRP)
- **Archivo:** `app/interface.py:339`
- **Severidad:** Baja
- **Descripción:** Mezcla UI, HTTP, lógica de negocio, estado global. `tk.Tk()` a nivel de módulo impide importar sin lanzar ventana.
- **Corrección:** Separar en: `ApiClient` (HTTP), lógica de presentación, y `main()` bajo `if __name__ == "__main__"`.

### 19. `interface.py` acoplado a `requests` concreto (DIP)
- **Archivo:** `app/interface.py`
- **Severidad:** Baja
- **Descripción:** Capa de presentación depende directamente de `requests` y serialización JSON del backend.
- **Corrección:** Introducir `ApiClient` inyectable (upload/list/get/patch/delete) que abstraiga el transporte.

### 20. Bug: `eliminar_historial` no limpia `texto_extraido_global` (UX)
- **Archivo:** `app/interface.py:242-265`
- **Severidad:** Media
- **Descripción:** Tras borrar documento, el texto sigue visible en `texto_resultado` (estado inconsistente).
- **Corrección:** En `eliminar_historial` → `texto_extraido_global = ""` + `texto_resultado.delete("1.0", tk.END)`.

### 21. Bug: `descargar_txt` usa memoria global, no documento seleccionado (lógica)
- **Archivo:** `app/interface.py:93-127`
- **Severidad:** Baja
- **Descripción:** Descarga siempre `texto_extraido_global` (último cargado), no el doc seleccionado en el historial.
- **Corrección:** Vincular descarga al documento activo (fetch del ID seleccionado) o clarificar UX explícito.

### 26. Nombre de archivo hardcodeado `"archivo.pdf"` en upload (consistencia)
- **Archivo:** `app/interface.py:49-50`
- **Severidad:** Baja
- **Descripción:** Multipart usa filename fijo `"archivo.pdf"`; backend guarda `pdf_nombre = "archivo.pdf"` perdiendo nombre real.
- **Corrección:** `os.path.basename(archivo_pdf)` en el campo `filename` del multipart.

---

## 🟡 PRIORIDAD MEDIA — Configuración y código muerto

### 5. Versiones Python inconsistentes en `pyproject.toml` / `Dockerfile`
- **Archivos:** `pyproject.toml`, `Dockerfile`
- **Severidad:** Baja
- **Descripción:** `requires-python=">=3.14"`, Docker `python:3.14`, pero `ruff target-version="py312"` y `mypy python_version="3.12"`.
- **Corrección:** Unificar a `py314` en ruff y mypy (requiere subir pins `ruff`/`mypy` + `uv lock`).

### 6. Dependencias duplicadas e inconsistentes en `pyproject.toml`
- **Archivo:** `pyproject.toml:22-29` y `91-96`
- **Severidad:** Media
- **Descripción:** Dos grupos `dev` (`[project.optional-dependencies]` y `[dependency-groups]`). `httpx2` inexistente. `pytest-mock` solo en `dependency-groups`.
- **Corrección:** Consolidar en `[dependency-groups]` (uv), fix `httpx2`→`httpx`, mover `pytest-mock`.

### 13. Código muerto / comentado en `pdf_service.py` (YAGNI)
- **Archivo:** `app/services/pdf_service.py:121-129, 160-161, 175-176`
- **Severidad:** Media
- **Descripción:** `_save_text_to_disk` nunca llamada (solo comentada). Bloques comentados líneas 160-161, 175-176. Constantes `TEXT_BLOCK`/`IMAGE_BLOCK` innecesarias.
- **Corrección:** Eliminar `_save_text_to_disk`, bloques comentados, y constantes de módulo si no se usan.

### 27. `except Exception` silencioso en OCR (robustez)
- **Archivo:** `app/services/pdf_service.py:58-64`
- **Severidad:** Media
- **Descripción:** Error en `pytesseract.image_to_string` se traga → `""`, oculta fallos y produce docs "ok" sin texto.
- **Corrección:** Propagar/loggear error nivel ERROR y marcar documento `error` (ver punto 25).

---

## 🟢 PRIORIDAD BAJA — DRY/KISS/YAGNI y bugs menores

### 11. Endpoints `by-checksum` y `get_by_id` duplicados (DRY)
- **Archivo:** `app/main.py:78-129`
- **Severidad:** Baja
- **Descripción:** Ambos devuelven `{"document_id": ..., "document": ...}` con patrón 404 idéntico.
- **Corrección:** Unificar mediante endpoint genérico o serializer compartido.

### 12. `_model_dump` legacy innecesario (YAGNI/KISS)
- **Archivo:** `app/main.py:49-52`
- **Severidad:** Baja
- **Descripción:** Helper contempla `model.dict()` "por si acaso"; pydantic v2 + Python 3.14 lo hace muerto.
- **Corrección:** Usar `payload.model_dump(exclude_unset=True)` directo y borrar helper.

### 14. `checksum_algoritmo="sha256"` hardcodeado (KISS)
- **Archivo:** `app/services/document_builder.py:34`
- **Severidad:** Baja
- **Descripción:** Siempre `"sha256"`; redundante persistirlo si no hay extensibilidad.
- **Corrección:** Eliminar campo o derivar de `checksum_service.calc_checksum` (nombre del algoritmo).

### 22. Limpieza redundante de `None` en `update_document` (bug/logic)
- **Archivo:** `app/main.py:138-141`
- **Severidad:** Media
- **Descripción:** `exclude_unset=True` ya excluye no-enviados; bloque `if updates.get(...) is None: pop()` es redundante y borra `None` legítimo.
- **Corrección:** Eliminar líneas 138-141.

### 24. `find_by_checksum` sin `include_text` (lógica)
- **Archivo:** `app/repositories/document_repository.py:76-79`
- **Severidad:** Baja
- **Descripción:** Endpoint `by-checksum` expone siempre `txt_contenido` completo (hasta 5 MB).
- **Corrección:** Añadir `include_text: bool = False` a `find_by_checksum` y pasar desde endpoint.

### 25. `estado="ok"` hardcodeado aunque texto vacío (lógica)
- **Archivo:** `app/services/pdf_service.py:185`
- **Severidad:** Baja
- **Descripción:** `process_pdf_upload` fuerza `"ok"` aunque `extract_text_from_pdf_bytes` devuelva `""` (OCR fallido).
- **Corrección:** Regla: si `texto_extraido == ""` → `estado = "error"` (o `"pendiente"`), no `"ok"`.

### 28. `except Exception` genérica en `_parse_document_id` (robustez)
- **Archivo:** `app/main.py:56-60`
- **Severidad:** Baja
- **Descripción:** Captura `Exception` al construir `ObjectId`; debería ser `bson.errors.InvalidId`.
- **Corrección:** `from bson.errors import InvalidId` y `except InvalidId`.

### 29. `DocumentUpdate.error` sin validación de coherencia (lógica)
- **Archivo:** `app/main.py:39-40`
- **Severidad:** Baja
- **Descripción:** Campo `error` actualizable libremente sin ligar a `estado == "error"`.
- **Corrección:** Validar en `update_document`: si `error` presente → requerir `estado == "error"`.

---

## 🟢 PRIORIDAD BAJA — Tests / Mantenibilidad

### 30. Tests acoplados a `tk.Tk()` (mantenibilidad)
- **Archivos:** `app/interface.py`, `tests/test_interface.py`
- **Severidad:** Media
- **Descripción:** `import app.interface` ejecuta `tk.Tk()` a nivel de módulo; tests fallan en CI sin display.
- **Corrección:** Requiere punto 18 primero (mover `Tk()` a `__main__`). Luego ajustar tests para no instanciar ventana.

### 31. Tests sin `__init__.py` ni fixtures de aislamiento (estructura)
- **Archivo:** `tests/`
- **Severidad:** Baja
- **Descripción:** Falta `tests/__init__.py`. Tests de `main` instancian `DocumentService()` con conexión real.
- **Corrección:** Añadir `__init__.py`, centralizar fixtures/mocks de `DocumentRepository` (evitar Mongo real en unit tests).

---

## Resumen por severidad (pendientes)

- **Media:** 16, 17, 15, 20, 6, 13, 27, 22, 30  (9 ítems)
- **Baja:** 5, 18, 19, 21, 26, 11, 12, 14, 24, 25, 28, 29, 31  (13 ítems)

---

## Orden de ejecución recomendado

1. **Inyección de dependencias** (16 + 17) — base para testeo y ciclo de vida Mongo
2. **Refactor `interface.py`** (15, 18, 19, 20, 21, 26) — desacople + bugs UX + URL config
3. **`pyproject.toml` cleanup** (5, 6) — tooling consistente + deps limpias
4. **Limpieza `pdf_service.py`** (13, 27) — código muerto + OCR robusto
5. **Resto DRY/KISS/bugs** (11, 12, 14, 22, 24, 25, 28, 29)
6. **Tests** (30, 31) — tras refactor `interface.py`, añadir fixtures y `__init__.py`