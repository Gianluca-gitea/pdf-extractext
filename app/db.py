from datetime import datetime, timezone
from pymongo import MongoClient
import time

mongo_uri = "mongodb://Usuario_bd:NcwXuCDKBmIWBrSv@ac-2modq9p-shard-00-00.fhhfn2f.mongodb.net:27017,ac-2modq9p-shard-00-01.fhhfn2f.mongodb.net:27017,ac-2modq9p-shard-00-02.fhhfn2f.mongodb.net:27017/?ssl=true&replicaSet=atlas-6mj7et-shard-0&authSource=admin&appName=pdf-extractext"


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
