import os
from datetime import datetime, timezone
import pymongo
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

from errors import DatabaseUnavailableError

load_dotenv()


class IngestionRepository:
    """
    MongoDB repository for managing ingestion records.
    Ensures state transitions are atomic, idempotent, and restricted to valid statuses.
    """

    def __init__(
        self,
        uri: str | None = None,
        db_name: str | None = None,
        collection_name: str | None = None,
    ):
        self.uri = uri or os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.db_name = db_name or os.getenv("MONGO_DB_NAME", "log_analytics")
        self.collection_name = collection_name or os.getenv("MONGO_COLLECTION", "ingestions")

        try:
            self.client = pymongo.MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
        except PyMongoError as e:
            raise DatabaseUnavailableError(f"Failed to connect to MongoDB: {e}") from e

    def insert_record(self, record: dict) -> str:
        """
        Inserts a new ingestion record into MongoDB.
        Returns the ingest_id.
        """
        try:
            self.collection.insert_one(record)
            return record["ingest_id"]
        except PyMongoError as e:
            raise DatabaseUnavailableError(f"Database error while inserting record: {e}") from e

    def find_by_id(self, ingest_id: str) -> dict | None:
        """
        Looks up an ingestion document by its unique `ingest_id` field (not MongoDB _id).
        """
        try:
            return self.collection.find_one({"ingest_id": ingest_id})
        except PyMongoError as e:
            raise DatabaseUnavailableError(f"Database error while finding ingest_id '{ingest_id}': {e}") from e

    def mark_processing(self, ingest_id: str) -> bool:
        """
        Conditional update: sets status to 'processing' and sets processing_started_at.
        Only allowed if current status is 'pending' or 'processing'.
        Returns True if record was updated, False if record was missing or completed/failed.
        """
        try:
            result = self.collection.update_one(
                {"ingest_id": ingest_id, "status": {"$in": ["pending", "processing"]}},
                {
                    "$set": {
                        "status": "processing",
                        "processing_started_at": datetime.now(timezone.utc),
                    }
                },
            )
            return result.matched_count > 0
        except PyMongoError as e:
            raise DatabaseUnavailableError(f"Database error marking '{ingest_id}' processing: {e}") from e

    def save_results(self, ingest_id: str, metrics: dict, report: dict, top_error: dict) -> bool:
        """
        Atomic update: sets status to 'completed', attaches metrics, report, and top_error.
        Only allowed if current status is 'pending' or 'processing'.
        Returns True if record was updated, False otherwise.
        """
        try:
            result = self.collection.update_one(
                {"ingest_id": ingest_id, "status": {"$in": ["pending", "processing"]}},
                {
                    "$set": {
                        "status": "completed",
                        "metrics": metrics,
                        "report": report,
                        "top_error": top_error,
                        "processed_at": datetime.now(timezone.utc),
                        "error_reason": None,
                    }
                },
            )
            return result.matched_count > 0
        except PyMongoError as e:
            raise DatabaseUnavailableError(f"Database error saving results for '{ingest_id}': {e}") from e

    def mark_failed(self, ingest_id: str, reason: str) -> bool:
        """
        Conditional update: sets status to 'failed' with error_reason.
        Only allowed if current status is 'pending' or 'processing'.
        Returns True if record was updated, False otherwise.
        """
        try:
            result = self.collection.update_one(
                {"ingest_id": ingest_id, "status": {"$in": ["pending", "processing"]}},
                {
                    "$set": {
                        "status": "failed",
                        "error_reason": reason,
                        "processed_at": datetime.now(timezone.utc),
                    }
                },
            )
            return result.matched_count > 0
        except PyMongoError as e:
            raise DatabaseUnavailableError(f"Database error marking '{ingest_id}' failed: {e}") from e
