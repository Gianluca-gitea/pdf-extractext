
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from pymongo import MongoClient, ReturnDocument
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

        actual_uri = mongo_client.address if hasattr(mongo_client, "address") else mongo_uri
        logger.info(
            "DocumentRepository initialized: uri=%s database=%s collection=%s",
            actual_uri,
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

    def _not_deleted_filter(self) -> dict:
        return {"$or": [{"deleted_at": None}, {"deleted_at": {"$exists": False}}]}

    def _apply_not_deleted_filter(self, base_query: dict, include_deleted: bool) -> dict:
        if include_deleted:
            return base_query

        return {"$and": [base_query, self._not_deleted_filter()]}

    def find_by_id(
        self,
        document_id: ObjectId,
        include_text: bool = True,
        include_deleted: bool = False,
    ) -> dict | None:
        logger.debug(
            "Finding document by id=%s include_text=%s include_deleted=%s",
            document_id,
            include_text,
            include_deleted,
        )
        query = self._apply_not_deleted_filter({"_id": document_id}, include_deleted)
        projection = None if include_text else {"txt_contenido": 0}
        return self.collection.find_one(query, projection)

    def find_by_checksum(self, checksum: str, include_deleted: bool = False) -> dict | None:
        logger.debug("Finding document by checksum=%s", checksum)
        query = self._apply_not_deleted_filter({"checksum_archivo": checksum}, include_deleted)
        return self.collection.find_one(query)

    def list_documents(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        include_text: bool = False,
        include_deleted: bool = False,
    ) -> list[dict]:
        logger.debug(
            "Listing documents: skip=%d limit=%d include_text=%s",
            skip,
            limit,
            include_text,
        )
        query = {} if include_deleted else self._not_deleted_filter()
        projection = None if include_text else {"txt_contenido": 0}
        cursor = self.collection.find(query, projection)

        cursor = cursor.sort([("created_at", -1), ("_id", -1)]).skip(skip).limit(limit)
        return list(cursor)

    def update_document(self, document_id: ObjectId, updates: dict) -> dict | None:
        logger.debug("Updating document id=%s fields=%s", document_id, list(updates.keys()))
        query = self._apply_not_deleted_filter({"_id": document_id}, include_deleted=False)
        return self.collection.find_one_and_update(
            query,
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )

    def delete_document(self, document_id: ObjectId) -> bool:
        logger.debug("Soft deleting document id=%s", document_id)
        query = self._apply_not_deleted_filter({"_id": document_id}, include_deleted=False)
        deleted_at = datetime.now(timezone.utc)
        result = self.collection.find_one_and_update(
            query,
            {"$set": {"deleted_at": deleted_at}},
            return_document=ReturnDocument.AFTER,
        )
        return result is not None
