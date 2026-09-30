from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from pymongo import MongoClient

from app.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService
from app.settings import get_settings

_mongo_client: MongoClient | None = None


def get_mongo_client() -> MongoClient:
    global _mongo_client
    if _mongo_client is None:
        settings = get_settings()
        _mongo_client = MongoClient(settings.mongodb_uri)
    return _mongo_client


def get_document_repository(
    mongo_client: Annotated[MongoClient, Depends(get_mongo_client)],
) -> DocumentRepository:
    return DocumentRepository(mongo_client=mongo_client)


def get_document_service(
    repository: Annotated[DocumentRepository, Depends(get_document_repository)],
) -> DocumentService:
    return DocumentService(repository=repository)


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None