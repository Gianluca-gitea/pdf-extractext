from fastapi import FastAPI, File, HTTPException, UploadFile

from app.settings import get_settings


settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/documents/upload")
async def upload_pdf(file: UploadFile = File(...)) -> dict[str, str | int]:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="El archivo esta vacio.")

    return {
        "filename": file.filename or "sin_nombre.pdf",
        "content_type": file.content_type,
        "size_bytes": len(file_bytes),
        "status": "uploaded",
    }
