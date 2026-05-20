
from __future__ import annotations

import logging
import os

from pymongo import MongoClient
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DocumentRepository:
    def __init__(self, mongo_client: MongoClient | None = None):
        if mongo_client is None:
            mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
            mongo_client = MongoClient(mongo_uri)

        self.client = mongo_client
        database_name = os.getenv("MONGODB_DB_NAME", "pdf-extractext")
        collection_name = os.getenv("MONGO_COLLECTION_NAME", "documents")

        self.db = mongo_client[database_name]
        self.collection = self.db[collection_name]

        logger.info(
            "DocumentRepository initialized: uri=%s database=%s collection=%s",
            mongo_client.address if hasattr(mongo_client, 'address') else os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
            database_name,
            collection_name,
        )

    def save_document(self, document: dict) -> ObjectId:
        result = self.collection.insert_one(document)
        logger.info(
            "Saved document: checksum=%s inserted_id=%s",
            document.get("checksum_archivo"),
            result.inserted_id,
        )
        return result.inserted_id

    def find_by_id(self, document_id: ObjectId) -> dict | None:
        logger.debug("Finding document by id=%s", document_id)
        return self.collection.find_one({"_id": document_id})

    def find_by_checksum(self, checksum: str) -> dict | None:
        logger.debug("Finding document by checksum=%s", checksum)
        return self.collection.find_one({"checksum_archivo": checksum})
