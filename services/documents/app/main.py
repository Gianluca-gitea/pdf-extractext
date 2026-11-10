from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
import logging
from app.messages import DEPENDENCIES_UNAVAILABLE
from starlette.formparsers import MultiPartParser
from app import __version__
from app.logging_config import configure_logging
from app.repositories.document_repository import close_document_repository
from app.services.extract_client import close_extract_client
from app.settings import get_settings

load_dotenv()
from app.routes import documents, upload, health

settings = get_settings()
configure_logging(settings.log_level)
MultiPartParser.spool_max_size = sys.maxsize


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        yield
    finally:
        close_extract_client()
        close_document_repository()


app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
for router in (health.router, documents.router, upload.router):
    app.include_router(router)


@app.exception_handler(PyMongoError)
async def database_error(request: Request, exc: PyMongoError):
    logging.getLogger(__name__).error("Database operation failed: %s", type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": DEPENDENCIES_UNAVAILABLE})
