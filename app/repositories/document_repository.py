
from __future__ import annotations

import os

from pymongo import MongoClient
from bson.objectid import ObjectId


class DocumentRepository:


    def __init__(self, mongo_client: MongoClient | None = None):

        if mongo_client is None:
            mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
            mongo_client = MongoClient(mongo_uri)
        
        self.client = mongo_client
        database_name = os.getenv("MONGO_DB_NAME", "pdf_extractext")
        collection_name = os.getenv("MONGO_COLLECTION_NAME", "documents")

        self.db = mongo_client[database_name]
        self.collection = self.db[collection_name]

    def save_document(self, document: dict) -> ObjectId:

        result = self.collection.insert_one(document)
        return result.inserted_id

    def find_by_id(self, document_id: ObjectId) -> dict | None:

        return self.collection.find_one({"_id": document_id})

    def find_by_checksum(self, checksum: str) -> dict | None:

        return self.collection.find_one({"checksum_archivo": checksum})
