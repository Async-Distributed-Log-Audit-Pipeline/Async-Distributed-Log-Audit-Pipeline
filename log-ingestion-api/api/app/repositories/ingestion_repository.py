"""
Amazon DynamoDB ingestion repository (replaces the MongoDB repository).

Table design (single table, created by template.yaml):
  Partition key : ingest_id (S)
  GSI entity-created_at-index : entity (S, constant "LOG") + created_at (S)  -> newest-first listing
  GSI status-created_at-index : status (S)               + created_at (S)  -> filter by status / metrics

Timestamps are stored as fixed-width ISO-8601 UTC strings so they sort correctly as strings.
DynamoDB has no float type, so floats are stored as Decimal and converted back on read.
"""

from datetime import datetime, timezone
from decimal import Decimal
from functools import lru_cache
import json
import logging
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

ENTITY_VALUE = "LOG"
ENTITY_INDEX = "entity-created_at-index"
STATUS_INDEX = "status-created_at-index"


class DatabaseUnavailableError(Exception):
    """Raised when DynamoDB is unreachable or throttles/fails."""


def to_iso(value: datetime) -> str:
    """Fixed-width UTC ISO string (always has microseconds) so string order == time order."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _to_dynamo(obj: Any) -> Any:
    """Recursively convert Python values into DynamoDB-safe values."""
    if isinstance(obj, datetime):
        return to_iso(obj)
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dynamo(v) for v in obj]
    return obj


def _from_dynamo(obj: Any) -> Any:
    """Recursively convert DynamoDB values back into JSON-friendly Python values."""
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    if isinstance(obj, dict):
        return {k: _from_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_from_dynamo(v) for v in obj]
    return obj


def _clean(item: Dict[str, Any]) -> Dict[str, Any]:
    out = _from_dynamo(item)
    out.pop("entity", None)  # internal GSI key, not part of the API contract
    return out


class IngestionRepository:
    def __init__(self, table_name: str, region: str = "us-east-1"):
        self.table_name = table_name
        self.table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    def insert_record(self, record: Dict[str, Any]) -> str:
        item = _to_dynamo(record)
        item["entity"] = ENTITY_VALUE
        try:
            self.table.put_item(Item=item, ConditionExpression="attribute_not_exists(ingest_id)")
            return record["ingest_id"]
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to insert ingestion record '%s': %s", record.get("ingest_id"), e)
            raise DatabaseUnavailableError(f"Database insert error: {e}") from e

    def find_by_id(self, ingest_id: str) -> Optional[Dict[str, Any]]:
        try:
            resp = self.table.get_item(Key={"ingest_id": ingest_id}, ConsistentRead=True)
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to query ingest_id '%s': %s", ingest_id, e)
            raise DatabaseUnavailableError(f"Database query error: {e}") from e
        item = resp.get("Item")
        return _clean(item) if item else None

    def find_all(
        self,
        service_name: Optional[str] = None,
        status: Optional[str] = None,
        environment: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        """Newest-first listing with optional filters and offset pagination."""
        limit = min(limit, 200)
        wanted = skip + limit

        if status:
            index, key_cond = STATUS_INDEX, Key("status").eq(status)
        else:
            index, key_cond = ENTITY_INDEX, Key("entity").eq(ENTITY_VALUE)

        filt = None
        for attr, val in (("service_name", service_name), ("environment", environment)):
            if val:
                cond = Attr(attr).eq(val)
                filt = cond if filt is None else filt & cond

        kwargs: Dict[str, Any] = {
            "IndexName": index,
            "KeyConditionExpression": key_cond,
            "ScanIndexForward": False,
        }
        if filt is not None:
            kwargs["FilterExpression"] = filt

        items: List[Dict[str, Any]] = []
        try:
            while len(items) < wanted:
                resp = self.table.query(**kwargs)
                items.extend(resp.get("Items", []))
                last = resp.get("LastEvaluatedKey")
                if not last:
                    break
                kwargs["ExclusiveStartKey"] = last
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to query log records list: %s", e)
            raise DatabaseUnavailableError(f"Database query error: {e}") from e

        return [_clean(i) for i in items[skip:wanted]]

    def mark_failed_if_pending(self, ingest_id: str, error_reason: str) -> bool:
        """Transition pending -> failed only if still pending (conditional write, race-safe)."""
        try:
            self.table.update_item(
                Key={"ingest_id": ingest_id},
                UpdateExpression="SET #s = :failed, #reason = :reason, #processed = :now",
                ConditionExpression="#s = :pending",
                ExpressionAttributeNames={"#s": "status", "#reason": "error_reason", "#processed": "processed_at"},
                ExpressionAttributeValues={
                    ":failed": "failed",
                    ":pending": "pending",
                    ":reason": error_reason,
                    ":now": to_iso(datetime.now(timezone.utc)),
                },
            )
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            logger.error("Failed to mark ingest_id '%s' as failed: %s", ingest_id, e)
            raise DatabaseUnavailableError(f"Database update error: {e}") from e
        except BotoCoreError as e:
            raise DatabaseUnavailableError(f"Database update error: {e}") from e

    def aggregate_completed_metrics(
        self,
        service_name: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Sum counters of completed jobs per service and derive a health rating."""
        key_cond = Key("status").eq("completed")
        if from_time and to_time:
            key_cond = key_cond & Key("created_at").between(to_iso(from_time), to_iso(to_time))
        elif from_time:
            key_cond = key_cond & Key("created_at").gte(to_iso(from_time))
        elif to_time:
            key_cond = key_cond & Key("created_at").lte(to_iso(to_time))

        kwargs: Dict[str, Any] = {
            "IndexName": STATUS_INDEX,
            "KeyConditionExpression": key_cond,
            "ProjectionExpression": "#sn, #m",
            "ExpressionAttributeNames": {"#sn": "service_name", "#m": "metrics"},
        }
        if service_name:
            kwargs["FilterExpression"] = Attr("service_name").eq(service_name)

        groups: Dict[str, Dict[str, int]] = {}
        try:
            while True:
                resp = self.table.query(**kwargs)
                for item in resp.get("Items", []):
                    item = _from_dynamo(item)
                    g = groups.setdefault(
                        item["service_name"],
                        {"total_logs": 0, "error_count": 0, "warning_count": 0, "critical_count": 0},
                    )
                    m = item.get("metrics") or {}
                    for k in g:
                        g[k] += int(m.get(k) or 0)
                last = resp.get("LastEvaluatedKey")
                if not last:
                    break
                kwargs["ExclusiveStartKey"] = last
        except (ClientError, BotoCoreError) as e:
            logger.error("Failed to aggregate metrics: %s", e)
            raise DatabaseUnavailableError(f"Database aggregation error: {e}") from e

        output = []
        for name in sorted(groups):
            g = groups[name]
            if g["critical_count"] > 0:
                health = "critical"
            elif g["error_count"] > 0:
                health = "degraded"
            elif g["warning_count"] > 0:
                health = "warning"
            else:
                health = "healthy"
            output.append({"service_name": name, **g, "health": health})
        return output


@lru_cache(maxsize=4)
def _build_repository(table_name: str, region: str) -> IngestionRepository:
    return IngestionRepository(table_name=table_name, region=region)


def get_ingestion_repository(settings: Settings = Depends(get_settings)) -> IngestionRepository:
    return _build_repository(settings.DDB_TABLE_NAME, settings.AWS_REGION)
