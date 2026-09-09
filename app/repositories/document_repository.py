
from __future__ import annotations

import logging
from datetime import datetime, timezone

from bson.objectid import ObjectId
from pymongo import MongoClient, ReturnDocument

from app.settings import Settings, get_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DocumentRepository:
    def __init__(
        self,
        settings: Settings | None = None,
        mongo_client: MongoClient | None = None,
    ):
        app_settings = settings or get_settings()

        self.client = mongo_client or MongoClient(app_settings.mongodb_uri)
        self.db = self.client[app_settings.mongodb_db_name]
        self.collection = self.db[app_settings.mongo_collection_name]

        actual_uri = (
            self.client.address
            if hasattr(self.client, "address")
            else app_settings.mongodb_uri
        )
        logger.info(
            "DocumentRepository initialized: uri=%s database=%s collection=%s",
            actual_uri,
            app_settings.mongodb_db_name,
            app_settings.mongo_collection_name,
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
