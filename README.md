# PDF Extract Text

## Descripción
Este proyecto fue desarrollado con el objetivo de extraer texto de archivos de una forma automática. 
La idea surge para tener que evitarnos estar copiando contenido de una forma manual, facilitando así de una forma sencilla el procesamiento de documentos

## Objetivos
Nuestro objetivo es desarrollar una herramienta simple y funcional que permita procesar archivos PDF y obtener su contenido de forma rápida y eficiente.

## Funcionalidades
- Permite extraer texto desde archivos pdf
- Facilita el manejo de informacion contenida en documentos

## Arquitectura
El proyecto funciona como una API HTTP sobre FastAPI.

- Capa de presentación: endpoints de FastAPI definidos en `app/main.py`.
- Capa de lógica: procesamiento y extracción de texto en `app/services/pdf_service.py`.
- Capa de datos: actualmente no persiste en base de datos; el texto se procesa en memoria y se devuelve en la respuesta.

## Estructura
- `app/main.py`: aplicación FastAPI y endpoints.
- `app/services/pdf_service.py`: lógica de extracción de texto y OCR.
- `app/settings.py`: configuración de la aplicación.
- `tests/`: pruebas automatizadas.

## Tecnologías usadas
- Python 3.12+
- FastAPI
- Uvicorn
- UV
- pypdf
- PyMuPDF
- OCRmyPDF
- python-multipart

> MongoDB es una mejora futura; actualmente no está integrada en el código.

> Se planea resumen por IA

> Se planea devolucíon como `.txt`

## Instalación
Este proyecto utiliza **`uv`** para gestionar dependencias.

1. Instalar `uv` (si no está instalado):
   ```bash
   pip install uv
   ```

2. Sincronizar el entorno virtual e instalar las dependencias:
   ```bash
   uv sync
   ```

3. Activar el entorno virtual:
   ```bash
   # En Windows
   .venv\Scripts\activate
   
   # En macOS/Linux
   source .venv/bin/activate
   ```

## API
- `GET /health`
  - Retorna `{ "status": "ok" }`.
- `POST /documents/upload`
  - Campo `file`: archivo PDF.
  - Respuestas posibles:
    - `200`: texto extraído y metadatos.
    - `400`: archivo vacío, contenido inválido o `content_type` incorrecto.
    - `413`: archivo demasiado grande.
  - Retorna:
    - `filename`
    - `content_type`
    - `size_bytes`
    - `extracted_text`
    - `status`

## Uso
Este proyecto se ejecuta como una API web con FastAPI.

Para iniciar el servidor en modo desarrollo:

```bash
uv run uvicorn app.main:app --reload
```

Para subir un PDF y extraer su texto, realiza un `POST` al endpoint `/documents/upload` con el archivo en un campo `file`.

Ejemplo con `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/documents/upload" \
  -F "file=@documento.pdf"
```
> Nota: la interfaz de usuario aún está en desarrollo. Actualmente la interacción es por `curl` o cliente HTTP; está planeado un HTML sencillo para la carga de PDFs y la visualización del texto extraído.

## Configuración
- `APP_MAX_PDF_SIZE_BYTES`: límite máximo de tamaño de PDF en bytes. Por defecto es `5242880` (5 MB).

## Pruebas
Ejecuta las pruebas con:

```bash
uv run pytest
```

