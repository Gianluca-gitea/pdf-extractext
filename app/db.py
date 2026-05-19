from datetime import datetime, timezone
from pymongo import MongoClient

from app.settings import get_settings

settings = get_settings()
mongo_client = MongoClient(settings.mongo_uri)

#para guardar en la base de datos, el formato es el siguiente:
{
    "pdf_nombre": str,  #El nombre del archivo PDF
    "txt_contenido": str,   #El contenido del archivo txt
    "txt_chars": int,   #La cantidad de caracteres del contenido del txt
    "estado": "ok" | "error",   #El estado de procesamiento del PDF, solo puede ser "ok" o "error"
    "error": str | None,    #Si el proceso devuelve error, aqui muestra el error, de lo contrario devuelve none
    "created_at": datetime, #La fecha y hora en que se creó el registro
    "duracion_ms": int  #La duración del proceso en ms
}
