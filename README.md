# PDF Extract Text

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)
![MongoDB](https://img.shields.io/badge/MongoDB-%234ea94b.svg?logo=mongodb&logoColor=white)
![Tkinter](https://img.shields.io/badge/UI-Tkinter-lightgrey)

---

## Descripción
Este proyecto fue desarrollado con el objetivo de **extraer texto de archivos PDF** de una forma automática. 
La idea surge para tener que evitarnos estar copiando contenido de una forma manual, facilitando así de una forma sencilla el procesamiento de documentos.

---

## Objetivos
Nuestro objetivo es desarrollar una herramienta simple y funcional que permita procesar archivos PDF y obtener su contenido de forma rápida y eficiente.

---

## Funcionalidades
- Permite extraer texto desde archivos PDF.
- Facilita el manejo de información contenida en documentos.
- Persistencia en base de datos para no reprocesar archivos idénticos (Deduplicación por Checksum).
- Interfaz gráfica (GUI) para selección de archivos, visualización del historial y descarga directa en formato `.txt`.
- Procesamiento OCR para extraer texto de imágenes incrustadas.
- Borrado lógico (Soft delete) y edición de estado de los documentos.

---

## Arquitectura
El proyecto funciona con una arquitectura cliente-servidor:

- **Capa de presentación (Frontend):** Interfaz de escritorio desarrollada con Tkinter (`app/interface.py`).
- **Capa de presentación (Backend):** Endpoints de FastAPI definidos en `app/main.py`.
- **Capa de servicio:** Gestión estricta de estados y validación de reglas de negocio (`app/services/document_service.py`).
- **Capa de lógica:** Procesamiento, cálculo de checksums y extracción de texto en `app/services/pdf_service.py`.
- **Capa de datos:** Los documentos y sus textos extraídos se persisten en **MongoDB** para acceso rápido e histórico (`app/repositories/document_repository.py`).

---

## Estructura
- `app/interface.py`: Interfaz gráfica de usuario.
- `app/main.py`: Aplicación FastAPI y endpoints.
- `app/services/`: Lógica de extracción de texto, OCR, gestión de estado y creación de documentos.
- `app/repositories/`: Lógica de conexión a la base de datos MongoDB.
- `app/settings.py`: Configuración de la aplicación.
- `tests/`: Pruebas automatizadas.
- `start.bat` / `start.sh`: Scripts para levantar el proyecto automáticamente.

---

## Tecnologías usadas
- Python 3.10+
- FastAPI & Uvicorn
- UV (Gestor de dependencias)
- PyMuPDF (`fitz`)
- pytesseract & Pillow (Para OCR de imágenes)
- pymongo (Base de datos)
- python-multipart
- Tkinter (Frontend)

> Se planea resumen por IA

---

## Requisitos Previos e Instalación
Este proyecto utiliza **`uv`** para gestionar dependencias.

**Requisitos del sistema:**
1. **MongoDB** debe estar instalado y corriendo en tu máquina (por defecto en el puerto `27017`).
[Descargar MongoDB](https://www.mongodb.com/try/download/community)
2. **Tesseract OCR** debe estar instalado en tu sistema operativo para que la extracción de texto en imágenes funcione correctamente.
[Descargar Tesseract](https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe)

**Instalación:**
1. Instalar `uv` (si no está instalado):
   ```bash
   pip install uv
   ```

2. Sincronizar el entorno virtual e instalar las dependencias:
    ```bash
    uv sync
    ```

---

## Uso

El proyecto cuenta con scripts de arranque que inicializan el entorno virtual, encienden el servidor backend (FastAPI) en segundo plano y abren la interfaz gráfica (Tkinter) automáticamente.

Para iniciar el proyecto completo, ejecuta el script correspondiente a tu sistema operativo en la raíz del proyecto:

**En Windows:**

```cmd
start.bat
```

**En Linux / macOS:**

```bash
./start.sh
```

---

## API

Si deseas usar el backend de forma independiente sin la interfaz, estos son los endpoints disponibles:

* `GET /health`
  * Retorna `{ "status": "ok" }`.


* `POST /documents/upload`
  * Campo `file`: archivo PDF.
  * Respuestas posibles:
  * `200`: texto extraído y metadatos.
  * `400`: archivo vacío, contenido inválido o `content_type` incorrecto.
  * `413`: archivo demasiado grande.


  * Retorna: `filename`, `content_type`, `size_bytes`, `extracted_text`, `status`.

* `GET /documents`

  * Retorna la lista paginada del historial de documentos.

  * Parámetros: `skip`, `limit`, `include_text`.

* `GET /documents/{document_id}`

  * Retorna un documento específico por su ID.

  * Parámetros: `include_text`.

* `PATCH /documents/{document_id}`

  * Permite actualizar el nombre del archivo (`pdf_nombre`) o su `estado`.

* `DELETE /documents/{document_id}`

  * Realiza un borrado lógico del documento en la base de datos (queda oculto sin perderse).


* `GET /documents/by-checksum/{checksum}`
  * Retorna un documento previamente procesado buscando por su hash SHA-256.


* `GET /documents/{document_id}/download`
  * Descarga directamente el texto extraído de un documento como un archivo `.txt`.

---

## Configuración

Las siguientes variables de entorno (o archivo `.env`) configuran el proyecto:

* `APP_MAX_PDF_SIZE_BYTES`: límite máximo de tamaño de PDF en bytes. Por defecto es `5242880` (5 MB).
* `MONGODB_URI`: URI de conexión a la base de datos (por defecto `mongodb://localhost:27017`).
* `MONGODB_DB_NAME`: Nombre de la base de datos (por defecto `pdf-extractext`).

---

## Pruebas

El proyecto cuenta con una cobertura exhaustiva de pruebas (unitarias, de integración y mocks de interfaz). Ejecuta las pruebas con:

```bash
uv run pytest
```
