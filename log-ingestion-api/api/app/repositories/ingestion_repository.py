"""
MongoDB Ingestion Repository.
Handles all persistence and query operations for log ingestion records in MongoDB.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from fastapi import Depends
import pymongo
from pymongo.errors import PyMongoError

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class DatabaseUnavailableError(Exception):
    """Raised when MongoDB connection or operation fails due to network/server issues."""
    pass


class IngestionRepository:
    """
    MongoDB repository for the 'ingestions' collection.
    Provides methods for inserting records, querying status, listing logs, and running metrics aggregations.
    """

    def __init__(
        self,
        uri: str = "mongodb://localhost:27017",
        db_name: str = "log_analytics",
        collection_name: str = "ingestions",
    ):
        self.uri = uri
        self.db_name = db_name
        self.collection_name = collection_name
        try:
            self.client = pymongo.MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
        except PyMongoError as e:
            logger.error("Failed to connect to MongoDB at %s: %s", self.uri, e)
            raise DatabaseUnavailableError(f"Database connection error: {e}") from e

    def insert_record(self, record: Dict[str, Any]) -> str:
        """
        Inserts a new ingestion document into MongoDB.
        Returns the unique ingest_id string.
        """
        try:
            self.collection.insert_one(record)
            return record["ingest_id"]
        except PyMongoError as e:
            logger.error("Failed to insert ingestion record '%s': %s", record.get("ingest_id"), e)
            raise DatabaseUnavailableError(f"Database insert error: {e}") from e

    def find_by_id(self, ingest_id: str) -> Optional[Dict[str, Any]]:
        """
        Looks up a single ingestion record by its unique ingest_id field.
        Explicitly excludes the MongoDB internal '_id' from the result.
        """
        try:
            return self.collection.find_one({"ingest_id": ingest_id}, {"_id": 0})
        except PyMongoError as e:
            logger.error("Failed to query ingest_id '%s': %s", ingest_id, e)
            raise DatabaseUnavailableError(f"Database query error: {e}") from e

    def find_all(
        self,
        service_name: Optional[str] = None,
        status: Optional[str] = None,
        environment: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Queries ingestion records sorted by created_at in descending order (newest first).
        Supports filtering by service_name, status, and environment, along with pagination.
        Explicitly excludes MongoDB internal '_id' from all returned documents.
        """
        query: Dict[str, Any] = {}
        if service_name:
            query["service_name"] = service_name
        if status:
            query["status"] = status
        if environment:
            query["environment"] = environment

        try:
            cursor = (
                self.collection.find(query, {"_id": 0})
                .sort("created_at", pymongo.DESCENDING)
                .skip(skip)
                .limit(min(limit, 200))
            )
            return list(cursor)
        except PyMongoError as e:
            logger.error("Failed to query log records list: %s", e)
            raise DatabaseUnavailableError(f"Database query error: {e}") from e

    def mark_failed_if_pending(self, ingest_id: str, error_reason: str) -> bool:
        """
        Conditionally transitions a job status to 'failed' ONLY if it is currently 'pending'.
        Used for failure handling when downstream queuing fails.
        """
        try:
            result = self.collection.update_one(
                {"ingest_id": ingest_id, "status": "pending"},
                {
                    "$set": {
                        "status": "failed",
                        "error_reason": error_reason,
                        "processed_at": datetime.now(timezone.utc),
                    }
                },
            )
            return result.matched_count > 0
        except PyMongoError as e:
            logger.error("Failed to mark ingest_id '%s' as failed: %s", ingest_id, e)
            raise DatabaseUnavailableError(f"Database update error: {e}") from e

    def aggregate_completed_metrics(
        self,
        service_name: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregates metrics for completed ingestion jobs grouped by service_name.
        Sums: metrics.total_logs, metrics.error_count, metrics.warning_count, metrics.critical_count.
        """
        match_stage: Dict[str, Any] = {"status": "completed"}
        if service_name:
            match_stage["service_name"] = service_name

        date_filter: Dict[str, Any] = {}
        if from_time:
            date_filter["$gte"] = from_time
        if to_time:
            date_filter["$lte"] = to_time

        if date_filter:
            match_stage["created_at"] = date_filter

        pipeline = [
            {"$match": match_stage},
            {
                "$group": {
                    "_id": "$service_name",
                    "total_logs": {"$sum": {"$ifNull": ["$metrics.total_logs", 0]}},
                    "error_count": {"$sum": {"$ifNull": ["$metrics.error_count", 0]}},
                    "warning_count": {"$sum": {"$ifNull": ["$metrics.warning_count", 0]}},
                    "critical_count": {"$sum": {"$ifNull": ["$metrics.critical_count", 0]}},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        try:
            results = list(self.collection.aggregate(pipeline))
            output = []
            for item in results:
                crit = int(item.get("critical_count", 0))
                err = int(item.get("error_count", 0))
                warn = int(item.get("warning_count", 0))
                tot = int(item.get("total_logs", 0))

                # Operational Health Rule:
                # 'critical' if critical_count > 0; else 'degraded' if error_count > 0; else 'warning' if warning_count > 0; else 'healthy'
                if crit > 0:
                    health = "critical"
                elif err > 0:
                    health = "degraded"
                elif warn > 0:
                    health = "warning"
                else:
                    health = "healthy"

                output.append({
                    "service_name": item["_id"],
                    "total_logs": tot,
                    "error_count": err,
                    "warning_count": warn,
                    "critical_count": crit,
                    "health": health,
                })
            return output
        except PyMongoError as e:
            logger.error("Failed to execute metrics aggregation pipeline: %s", e)
            raise DatabaseUnavailableError(f"Database aggregation error: {e}") from e


class DynamoDBIngestionRepository:
    """
    AWS DynamoDB repository for the 'ingestions' table.
    Provides identical persistence & query interface for serverless cloud deployment.
    """

    def __init__(self, table_name: str = "ingestions", region: str = "us-east-1"):
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError

        self.table_name = table_name
        self.region = region
        try:
            self.dynamodb = boto3.resource("dynamodb", region_name=self.region)
            self.table = self.dynamodb.Table(self.table_name)
        except Exception as e:
            logger.error("Failed to initialize DynamoDB connection: %s", e)
            raise DatabaseUnavailableError(f"DynamoDB connection error: {e}") from e

    def _serialize_for_dynamodb(self, data: Any) -> Any:
        from decimal import Decimal
        if isinstance(data, float):
            return Decimal(str(data))
        if isinstance(data, datetime):
            return data.isoformat()
        if isinstance(data, dict):
            return {k: self._serialize_for_dynamodb(v) for k, v in data.items() if v is not None}
        if isinstance(data, list):
            return [self._serialize_for_dynamodb(v) for v in data]
        return data

    def insert_record(self, record: Dict[str, Any]) -> str:
        try:
            item = self._serialize_for_dynamodb(record)
            self.table.put_item(Item=item)
            return record["ingest_id"]
        except Exception as e:
            logger.error("Failed to insert record '%s' into DynamoDB: %s", record.get("ingest_id"), e)
            raise DatabaseUnavailableError(f"DynamoDB insert error: {e}") from e

    def find_by_id(self, ingest_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.table.get_item(Key={"ingest_id": ingest_id})
            return response.get("Item")
        except Exception as e:
            logger.error("Failed to query ingest_id '%s' from DynamoDB: %s", ingest_id, e)
            raise DatabaseUnavailableError(f"DynamoDB query error: {e}") from e

    def find_all(
        self,
        service_name: Optional[str] = None,
        status: Optional[str] = None,
        environment: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        from boto3.dynamodb.conditions import Attr
        try:
            filter_exp = None
            if service_name:
                filter_exp = Attr("service_name").eq(service_name)
            if status:
                st_filter = Attr("status").eq(status)
                filter_exp = filter_exp & st_filter if filter_exp else st_filter
            if environment:
                env_filter = Attr("environment").eq(environment)
                filter_exp = filter_exp & env_filter if filter_exp else env_filter

            scan_kwargs: Dict[str, Any] = {"Limit": min(limit + skip, 200)}
            if filter_exp:
                scan_kwargs["FilterExpression"] = filter_exp

            response = self.table.scan(**scan_kwargs)
            items = response.get("Items", [])
            # Sort by created_at descending if available
            items.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
            return items[skip : skip + limit]
        except Exception as e:
            logger.error("Failed to scan DynamoDB records: %s", e)
            raise DatabaseUnavailableError(f"DynamoDB scan error: {e}") from e

    def mark_failed_if_pending(self, ingest_id: str, error_reason: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.table.update_item(
                Key={"ingest_id": ingest_id},
                UpdateExpression="SET #st = :failed, error_reason = :reason, processed_at = :now",
                ConditionExpression="#st = :pending",
                ExpressionAttributeNames={"#st": "status"},
                ExpressionAttributeValues={
                    ":failed": "failed",
                    ":reason": error_reason,
                    ":now": datetime.now(timezone.utc).isoformat(),
                    ":pending": "pending",
                },
            )
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise DatabaseUnavailableError(f"DynamoDB update error: {e}") from e
        except Exception as e:
            raise DatabaseUnavailableError(f"DynamoDB update error: {e}") from e

    def aggregate_completed_metrics(
        self,
        service_name: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        from boto3.dynamodb.conditions import Attr
        try:
            filter_exp = Attr("status").eq("completed")
            if service_name:
                filter_exp = filter_exp & Attr("service_name").eq(service_name)

            response = self.table.scan(FilterExpression=filter_exp)
            items = response.get("Items", [])

            service_map: Dict[str, Dict[str, int]] = {}
            for item in items:
                svc = item.get("service_name", "unknown")
                metrics = item.get("metrics") or {}
                if svc not in service_map:
                    service_map[svc] = {
                        "total_logs": 0,
                        "error_count": 0,
                        "warning_count": 0,
                        "critical_count": 0,
                    }
                service_map[svc]["total_logs"] += int(metrics.get("total_logs", 0))
                service_map[svc]["error_count"] += int(metrics.get("error_count", 0))
                service_map[svc]["warning_count"] += int(metrics.get("warning_count", 0))
                service_map[svc]["critical_count"] += int(metrics.get("critical_count", 0))

            output = []
            for svc_name, stats in sorted(service_map.items()):
                crit = stats["critical_count"]
                err = stats["error_count"]
                warn = stats["warning_count"]
                if crit > 0:
                    health = "critical"
                elif err > 0:
                    health = "degraded"
                elif warn > 0:
                    health = "warning"
                else:
                    health = "healthy"

                output.append({
                    "service_name": svc_name,
                    "total_logs": stats["total_logs"],
                    "error_count": err,
                    "warning_count": warn,
                    "critical_count": crit,
                    "health": health,
                })
            return output
        except Exception as e:
            logger.error("Failed to aggregate DynamoDB metrics: %s", e)
            raise DatabaseUnavailableError(f"DynamoDB aggregation error: {e}") from e


def get_ingestion_repository(
    settings: Settings = Depends(get_settings),
):
    """Dependency provider for IngestionRepository (MongoDB or DynamoDB)."""
    if settings.DB_TYPE.lower() == "dynamodb":
        return DynamoDBIngestionRepository(
            table_name=settings.DYNAMODB_TABLE_NAME,
            region=settings.S3_REGION,
        )
    return IngestionRepository(
        uri=settings.MONGO_URI,
        db_name=settings.MONGO_DB_NAME,
        collection_name=settings.MONGO_COLLECTION,
    )
