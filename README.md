# PDF Extract Text

![Python](https://img.shields.io/badge/Python-3.14+-blue.svg?logo=python&logoColor=white)
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
- Convierte PDFs a Markdown (`POST /extract`), con títulos detectados por tamaño de fuente.
- Arquitectura de microservicios: la extracción y la gestión de documentos se despliegan y escalan por separado.
- Facilita el manejo de información contenida en documentos.
- Persistencia en base de datos para no reprocesar archivos idénticos (Deduplicación por Checksum).
- Interfaz gráfica (GUI) para selección de archivos, visualización del historial y descarga directa en formato `.txt` o `.md`.
- Procesamiento OCR opcional para extraer texto de imágenes incrustadas (desactivado por defecto, se activa con `APP_OCR_ENABLED=true`).
- Borrado lógico (Soft delete) y edición de estado de los documentos.

---

## Arquitectura
El backend está dividido en dos microservicios FastAPI que se comunican por HTTP, detrás de un gateway **nginx**:

```
GUI (Tkinter) · k6 · Vegeta
          │
   nginx :8000  (gateway)
   ├── /extract*   ──►  extract   ×5   (sin estado, PyMuPDF)
   └── /documents* ──►  documents ×1 ──► MongoDB
                            │
                            └── POST /extract/text ──► extract
```

- **extract** (`services/extract/`): recibe un PDF y devuelve el texto en Markdown (`/extract`) o en texto plano (`/extract/text`). No guarda nada y no conoce la base de datos. Es el que consume CPU, por eso corre con 5 réplicas, un hilo de extracción dedicado y una cola acotada que responde `503` al llenarse.
- **documents** (`services/documents/`): historial de documentos en **MongoDB**, deduplicación por checksum SHA-256, estados y borrado lógico. Al recibir un upload calcula el checksum y, solo si el PDF es nuevo, le pide el texto a extract.
- **nginx** (`nginx/`): punto de entrada único en el puerto `8000`. Rutea por path a cada servicio y reparte la carga entre las réplicas con `least_conn`.
- **GUI** (`gui/`): interfaz de escritorio que consume la API a través del gateway.

Cada servicio tiene su propio `pyproject.toml`, `uv.lock`, `Dockerfile` y tests, así que se instala, se prueba y se despliega por separado.

---

## Estructura

```
.
├── services
│   ├── extract
│   │   ├── app
│   │   │   ├── main.py            # /extract, /extract/text, /health
│   │   │   ├── pdf_service.py     # PyMuPDF → texto / Markdown, OCR
│   │   │   └── settings.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   └── documents
│       ├── app
│       │   ├── main.py            # /documents/*, /health
│       │   ├── repositories/document_repository.py
│       │   ├── services
│       │   │   ├── extract_client.py   # cliente HTTP hacia extract
│       │   │   ├── upload_service.py   # checksum → duplicado → extraer → guardar
│       │   │   ├── document_service.py
│       │   │   ├── document_builder.py
│       │   │   └── checksum_service.py
│       │   ├── admin/create_indexes.py
│       │   └── settings.py
│       ├── tests/
│       ├── Dockerfile
│       └── pyproject.toml
├── gui
│   ├── interface.py
│   ├── tests/
│   └── pyproject.toml
├── nginx/templates/default.conf.template
├── tests/stress/                  # k6 y Vegeta
├── docker-compose.yml
└── start.sh / start.bat
```

- `services/extract/`: microservicio de extracción de texto, Markdown y OCR.
- `services/documents/`: microservicio de persistencia, deduplicación y estados.
- `gui/`: interfaz gráfica de usuario.
- `nginx/`: gateway que rutea a cada servicio y balancea entre réplicas.
- `tests/stress/`: pruebas de carga con k6 (`spike_tests.js`) y Vegeta (`vegeta_tests.sh`) sobre los PDFs de `tests/stress/pdfs/`.
- `start.bat` / `start.sh`: scripts para levantar el proyecto sin Docker.

---

## Tecnologías usadas
- Python 3.14+
- FastAPI & Uvicorn
- UV (Gestor de dependencias)
- PyMuPDF (`fitz`) — servicio extract
- pytesseract & Pillow (Para OCR de imágenes) — servicio extract
- pymongo (Base de datos) — servicio documents
- httpx (comunicación entre servicios) — servicio documents
- python-multipart
- nginx (gateway)
- Tkinter (Frontend)
- *Docker (Opcional)*

> Se planea resumen por IA

---

## Instalación y uso *sin* Docker

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

2. Sincronizar el entorno virtual de cada parte:
    ```bash
    uv --directory services/extract sync
    uv --directory services/documents sync
    uv --directory gui sync
    ```

**Uso**

Los scripts de arranque sincronizan las dependencias, levantan **extract** en el puerto `8001` y **documents** en el `8002` en segundo plano y abren la interfaz gráfica apuntando a cada uno. Sin Docker no hay gateway, por eso la GUI usa una URL por servicio (`EXTRACT_API_URL` y `DOCUMENTS_API_URL`).

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

## Instalación y uso *con* Docker

**Requisitos del sistema:**
1. **Docker** debe estar instalado y corriendo en tu máquina.
[Descargar Docker](https://www.docker.com/get-started)

**Instalación:**
1. Levantar los contenedores:
```bash
docker compose up --build
```

Esto levanta 5 réplicas de **extract** (cada una limitada a 1 CPU y 1 GB de RAM), 1 réplica de **documents**, **MongoDB** y el gateway **nginx**, que atiende en el puerto `8000`.

**Uso**
1. Instalar `uv` (si no está instalado):
```bash
pip install uv
```

2. Abrir la interfaz en otro cmd:
```bash
uv --directory gui run python interface.py
```

**Cerrar y relanzar los contenedores**

Los contenedores se pueden cerrar con las teclas `Ctrl+C`

Se vuelven a abrir corriendo:
```bash
docker compose up
```

---

## API

Si deseas usar el backend de forma independiente sin la interfaz, estos son los endpoints disponibles a través del gateway (`http://localhost:8000`):

* `GET /health`
  * Retorna `{ "status": "ok" }`. Cada servicio expone también su propio `/health`.

### Servicio extract

* `POST /extract`
  * Recibe el PDF como `multipart/form-data` (campo `file`) o como binario directo en el body (`Content-Type: application/pdf`).
  * No guarda nada en la base de datos.
  * Respuestas posibles:
  * `200`: `{ "content": "<texto en Markdown>", "page_count": <cantidad de páginas> }`.
  * `400`: archivo vacío, contenido inválido o falta el campo `file`.
  * `413`: archivo demasiado grande.
  * `503`: servicio saturado; reintentar luego de lo indicado en el header `Retry-After`.

* `POST /extract/text`
  * Igual que `/extract`, pero `content` es texto plano (sin títulos Markdown). Es el que usa documents para guardar el texto.

### Servicio documents

* `POST /documents/upload`
  * Campo `file`: archivo PDF.
  * Si el PDF ya fue procesado (mismo checksum) devuelve el documento existente sin volver a extraer.
  * Respuestas posibles:
  * `200`: texto extraído y metadatos.
  * `400`: archivo vacío, contenido inválido o `content_type` incorrecto.
  * `413`: archivo demasiado grande.
  * `502`: no se pudo contactar al servicio extract.
  * `503`: extract está saturado; reintentar luego de lo indicado en `Retry-After`.
  * `504`: extract no respondió a tiempo.


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

**Comunes a ambos servicios**
* `APP_MAX_PDF_SIZE_BYTES`: límite máximo de tamaño de PDF en bytes. Por defecto es `10485760` (10 MB).
* `APP_LOG_LEVEL`: nivel de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Por defecto es `INFO`.
* `PORT`: puerto en el que escucha el servicio dentro del contenedor. Por defecto es `8000`.

**Servicio extract**
* `APP_OCR_ENABLED`: activa el OCR de imágenes con `true`. Por defecto es `false`.
* `APP_EXTRACT_WORKERS`: cantidad de extracciones simultáneas por réplica. Por defecto es `1`.
* `APP_MAX_PENDING_EXTRACTIONS`: máximo de extracciones en curso o en espera por réplica; al superarlo, `/extract` y `/extract/text` responden `503`. Por defecto es `100`.

**Servicio documents**
* `MONGODB_URI`: URI de conexión a la base de datos (por defecto `mongodb://localhost:27017`).
* `MONGODB_DB_NAME`: Nombre de la base de datos (por defecto `pdf-extractext`).
* `MONGO_COLLECTION_NAME`: Nombre de la colección (por defecto `documents`).
* `EXTRACT_SERVICE_URL`: URL del servicio extract (por defecto `http://localhost:8001`; en Docker `http://extract:8000`).
* `EXTRACT_TIMEOUT_S`: segundos que espera la respuesta de extract antes de devolver `504`. Por defecto es `30`.

**GUI**
* `API_URL`: URL del gateway (por defecto `http://127.0.0.1:8000`).
* `EXTRACT_API_URL` / `DOCUMENTS_API_URL`: URL de cada servicio cuando no hay gateway. Por defecto toman el valor de `API_URL`.

---

## Procesos de administración

Los índices de MongoDB (incluido el índice único sobre `checksum_archivo`, que evita duplicados entre uploads simultáneos) se crean con un comando puntual del servicio documents, que usa el mismo código y la misma configuración que la API. Hay que correrlo una vez por base de datos y es seguro repetirlo:

```bash
uv --directory services/documents run python -m app.admin.create_indexes   # sin Docker
docker compose run --rm documents python -m app.admin.create_indexes       # con Docker
```

---

## Releases

El CI publica en GHCR una imagen por servicio (`pdf-extractext-extract` y `pdf-extractext-documents`) por cada push a `main`, etiquetada con el SHA del commit (`sha-<commit>`), y otra por cada tag `vX.Y.Z`. Para desplegar o volver a un release concreto:

```bash
IMAGE_TAG=sha-<commit> docker compose up -d --no-build
```

---

## Pruebas

Cada servicio y la GUI tienen sus propias pruebas (unitarias, de integración y mocks de interfaz), y se corren desde su carpeta:

```bash
uv --directory services/extract run pytest
uv --directory services/documents run pytest
uv --directory gui run pytest
```

> Los dos servicios tienen un paquete llamado `app`, así que `pytest`, `mypy` y `black` se corren siempre dentro de la carpeta de cada servicio, nunca desde la raíz.
