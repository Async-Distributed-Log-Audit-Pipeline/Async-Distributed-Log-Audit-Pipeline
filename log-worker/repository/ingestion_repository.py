"""
Amazon DynamoDB repository for the worker (replaces the MongoDB repository).

State transitions are enforced with DynamoDB *conditional writes*, so they are atomic and
idempotent even when SQS delivers the same message twice or two Lambdas race:
    pending/processing -> processing | completed | failed      (allowed)
    completed/failed   -> anything                             (rejected: stays terminal)
"""

from datetime import datetime, timezone
from decimal import Decimal
import os
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from errors import DatabaseUnavailableError

ACTIVE_STATES = {":pending": "pending", ":processing": "processing"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _to_dynamo(obj: Any) -> Any:
    """DynamoDB has no float type: floats become Decimal; datetimes become ISO strings."""
    if isinstance(obj, datetime):
        return obj.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dynamo(v) for v in obj]
    return obj


def _from_dynamo(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    if isinstance(obj, dict):
        return {k: _from_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_from_dynamo(v) for v in obj]
    return obj


def _is_condition_failure(err: ClientError) -> bool:
    return err.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"


class IngestionRepository:
    def __init__(self, table_name: str | None = None, region: str | None = None):
        self.table_name = table_name or os.getenv("DDB_TABLE_NAME", "log-ingestions")
        region = region or os.getenv("AWS_REGION", "us-east-1")
        self.table = boto3.resource("dynamodb", region_name=region).Table(self.table_name)

    def insert_record(self, record: dict) -> str:
        item = _to_dynamo(record)
        item["entity"] = "LOG"
        try:
            self.table.put_item(Item=item, ConditionExpression="attribute_not_exists(ingest_id)")
            return record["ingest_id"]
        except (ClientError, BotoCoreError) as e:
            raise DatabaseUnavailableError(f"Database error while inserting record: {e}") from e

    def find_by_id(self, ingest_id: str) -> dict | None:
        try:
            resp = self.table.get_item(Key={"ingest_id": ingest_id}, ConsistentRead=True)
        except (ClientError, BotoCoreError) as e:
            raise DatabaseUnavailableError(f"Database error while finding ingest_id '{ingest_id}': {e}") from e
        item = resp.get("Item")
        return _from_dynamo(item) if item else None

    def _conditional_update(self, ingest_id: str, update_expr: str, names: dict, values: dict) -> bool:
        """Apply update only while the record is pending/processing. Returns False if the condition fails."""
        names = {"#s": "status", **names}
        values = {**ACTIVE_STATES, **values}
        try:
            self.table.update_item(
                Key={"ingest_id": ingest_id},
                UpdateExpression=update_expr,
                ConditionExpression="#s IN (:pending, :processing)",
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=values,
            )
            return True
        except ClientError as e:
            if _is_condition_failure(e):
                return False
            raise DatabaseUnavailableError(f"Database error updating '{ingest_id}': {e}") from e
        except BotoCoreError as e:
            raise DatabaseUnavailableError(f"Database error updating '{ingest_id}': {e}") from e

    def mark_processing(self, ingest_id: str) -> bool:
        return self._conditional_update(
            ingest_id,
            "SET #s = :new_status, #started = :now",
            {"#started": "processing_started_at"},
            {":new_status": "processing", ":now": _now_iso()},
        )

    def save_results(self, ingest_id: str, metrics: dict, report: dict, top_error: str | None) -> bool:
        return self._conditional_update(
            ingest_id,
            "SET #s = :new_status, #metrics = :metrics, #report = :report, #top_error = :top_error, "
            "#processed = :now, #reason = :none",
            {"#metrics": "metrics", "#report": "report", "#top_error": "top_error",
             "#processed": "processed_at", "#reason": "error_reason"},
            {
                ":new_status": "completed",
                ":metrics": _to_dynamo(metrics),
                ":report": _to_dynamo(report),
                ":top_error": top_error,
                ":now": _now_iso(),
                ":none": None,
            },
        )

    def mark_failed(self, ingest_id: str, reason: str) -> bool:
        return self._conditional_update(
            ingest_id,
            "SET #s = :new_status, #reason = :reason, #processed = :now",
            {"#reason": "error_reason", "#processed": "processed_at"},
            {":new_status": "failed", ":reason": reason, ":now": _now_iso()},
        )
