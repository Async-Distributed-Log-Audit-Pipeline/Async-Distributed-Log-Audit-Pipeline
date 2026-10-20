import os
from datetime import datetime, timezone
import pymongo
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

from errors import DatabaseUnavailableError

load_dotenv()


class MongoIngestionRepository:
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
        try:
            self.collection.insert_one(record)
            return record["ingest_id"]
        except PyMongoError as e:
            raise DatabaseUnavailableError(f"Database error while inserting record: {e}") from e

    def find_by_id(self, ingest_id: str) -> dict | None:
        try:
            return self.collection.find_one({"ingest_id": ingest_id})
        except PyMongoError as e:
            raise DatabaseUnavailableError(f"Database error while finding ingest_id '{ingest_id}': {e}") from e

    def mark_processing(self, ingest_id: str) -> bool:
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


class DynamoDBWorkerRepository:
    """
    AWS DynamoDB repository for worker tasks.
    """

    def __init__(self, table_name: str | None = None, region: str | None = None):
        import boto3
        self.table_name = table_name or os.getenv("DYNAMODB_TABLE_NAME", "ingestions")
        self.region = region or os.getenv("S3_REGION", "us-east-1")
        try:
            self.dynamodb = boto3.resource("dynamodb", region_name=self.region)
            self.table = self.dynamodb.Table(self.table_name)
        except Exception as e:
            raise DatabaseUnavailableError(f"Failed to connect to DynamoDB: {e}") from e

    def _serialize(self, data):
        from decimal import Decimal
        if isinstance(data, float):
            return Decimal(str(data))
        if isinstance(data, datetime):
            return data.isoformat()
        if isinstance(data, dict):
            return {k: self._serialize(v) for k, v in data.items() if v is not None}
        if isinstance(data, list):
            return [self._serialize(v) for v in data]
        return data

    def insert_record(self, record: dict) -> str:
        try:
            item = self._serialize(record)
            self.table.put_item(Item=item)
            return record["ingest_id"]
        except Exception as e:
            raise DatabaseUnavailableError(f"DynamoDB error inserting: {e}") from e

    def find_by_id(self, ingest_id: str) -> dict | None:
        try:
            res = self.table.get_item(Key={"ingest_id": ingest_id})
            return res.get("Item")
        except Exception as e:
            raise DatabaseUnavailableError(f"DynamoDB error finding: {e}") from e

    def mark_processing(self, ingest_id: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.table.update_item(
                Key={"ingest_id": ingest_id},
                UpdateExpression="SET #st = :processing, processing_started_at = :now",
                ConditionExpression="#st IN (:pending, :processing)",
                ExpressionAttributeNames={"#st": "status"},
                ExpressionAttributeValues={
                    ":processing": "processing",
                    ":pending": "pending",
                    ":now": datetime.now(timezone.utc).isoformat(),
                },
            )
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise DatabaseUnavailableError(f"DynamoDB error: {e}") from e

    def save_results(self, ingest_id: str, metrics: dict, report: dict, top_error: dict) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.table.update_item(
                Key={"ingest_id": ingest_id},
                UpdateExpression="SET #st = :completed, metrics = :metrics, report = :report, top_error = :top_error, processed_at = :now, error_reason = :null",
                ConditionExpression="#st IN (:pending, :processing)",
                ExpressionAttributeNames={"#st": "status"},
                ExpressionAttributeValues={
                    ":completed": "completed",
                    ":pending": "pending",
                    ":processing": "processing",
                    ":metrics": self._serialize(metrics),
                    ":report": self._serialize(report),
                    ":top_error": self._serialize(top_error),
                    ":now": datetime.now(timezone.utc).isoformat(),
                    ":null": None,
                },
            )
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise DatabaseUnavailableError(f"DynamoDB error: {e}") from e

    def mark_failed(self, ingest_id: str, reason: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.table.update_item(
                Key={"ingest_id": ingest_id},
                UpdateExpression="SET #st = :failed, error_reason = :reason, processed_at = :now",
                ConditionExpression="#st IN (:pending, :processing)",
                ExpressionAttributeNames={"#st": "status"},
                ExpressionAttributeValues={
                    ":failed": "failed",
                    ":pending": "pending",
                    ":processing": "processing",
                    ":reason": reason,
                    ":now": datetime.now(timezone.utc).isoformat(),
                },
            )
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise DatabaseUnavailableError(f"DynamoDB error: {e}") from e


def IngestionRepository(*args, **kwargs):
    """Factory creating DynamoDB or Mongo repository depending on DB_TYPE."""
    db_type = os.getenv("DB_TYPE", "mongodb").lower()
    if db_type == "dynamodb":
        return DynamoDBWorkerRepository()
    return MongoIngestionRepository(*args, **kwargs)
