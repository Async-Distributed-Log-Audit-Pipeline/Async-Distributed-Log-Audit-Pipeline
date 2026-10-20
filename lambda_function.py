"""
AWS Lambda entry point for the log worker.

Trigger : Amazon SQS event source mapping (batch size 1..N, ReportBatchItemFailures enabled).
Flow    : SQS message -> process_message() -> DynamoDB status/metrics update (S3 file is parsed).

Delivery semantics (replaces the old RabbitMQ consumer loop):
  * ACK            -> message is simply not reported as a failure, so SQS deletes it.
  * RETRY          -> reported in batchItemFailures; visibility timeout is set to an exponential
                      backoff delay (retry_policy.compute_delay), so SQS redelivers it later.
  * DEAD_LETTER    -> copied to the DLQ with diagnostic attributes, record marked failed, then ACKed.
  * Crash/timeout  -> SQS redrive policy (maxReceiveCount) moves the message to the DLQ as a safety net.
Processing is idempotent (conditional DynamoDB writes), so duplicate deliveries are harmless.
"""

import logging
import os
import socket
from datetime import datetime, timezone

import boto3

from processor import process_message
from repository.ingestion_repository import IngestionRepository
from retry_policy import Action, compute_delay, decide_action
from storage.storage_client import ObjectStorageClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BASE_DELAY_SECONDS = float(os.getenv("RETRY_BASE_DELAY_SECONDS", "2"))
RETRY_MAX_DELAY_SECONDS = float(os.getenv("RETRY_MAX_DELAY_SECONDS", "60"))
QUEUE_URL = os.getenv("QUEUE_URL", "")
DLQ_URL = os.getenv("DLQ_URL", "")
WORKER_ID = os.getenv("AWS_LAMBDA_LOG_STREAM_NAME", socket.gethostname())

# Created once per container and reused across warm invocations.
_repo = None
_storage = None
_sqs = None


def _deps():
    global _repo, _storage, _sqs
    if _repo is None:
        _repo = IngestionRepository()
        _storage = ObjectStorageClient()
        _sqs = boto3.client("sqs", region_name=os.getenv("AWS_REGION", "us-east-1"))
    return _repo, _storage, _sqs


def _send_to_dlq(sqs, body: str, failure_type: str, reason: str | None, retry_count: int) -> None:
    sqs.send_message(
        QueueUrl=DLQ_URL,
        MessageBody=body,
        MessageAttributes={
            "failure_type": {"DataType": "String", "StringValue": failure_type},
            "failure_reason": {"DataType": "String", "StringValue": (str(reason) if reason else "Unknown reason")[:1000]},
            "retry_count": {"DataType": "Number", "StringValue": str(retry_count)},
            "failed_at": {"DataType": "String", "StringValue": datetime.now(timezone.utc).isoformat()},
            "worker_id": {"DataType": "String", "StringValue": str(WORKER_ID)[:200]},
        },
    )


def handler(event, context):
    repo, storage, sqs = _deps()
    failures = []

    for record in event.get("Records", []):
        message_id = record["messageId"]
        body = record["body"]
        receive_count = int(record.get("attributes", {}).get("ApproximateReceiveCount", "1"))
        retry_count = max(receive_count - 1, 0)

        try:
            result = process_message(body.encode("utf-8"), repo, storage)
        except Exception:  # process_message already catches most errors; this is the last line of defence
            logger.exception("[%s] Unhandled error; leaving message for redelivery", message_id)
            failures.append({"itemIdentifier": message_id})
            continue

        decision = decide_action(result, retry_count, MAX_RETRIES)
        ingest_str = result.ingest_id or "NO_ID"

        if decision.action == Action.ACK:
            logger.info("[%s] ACK (outcome=%s)", ingest_str, result.outcome.name)

        elif decision.action == Action.RETRY:
            delay = compute_delay(retry_count + 1, base=RETRY_BASE_DELAY_SECONDS, cap=RETRY_MAX_DELAY_SECONDS)
            logger.warning("[%s] Transient failure (attempt %d/%d). Retry in %.1fs. Reason: %s",
                           ingest_str, retry_count + 1, MAX_RETRIES, delay, result.reason)
            try:
                if QUEUE_URL:
                    sqs.change_message_visibility(
                        QueueUrl=QUEUE_URL,
                        ReceiptHandle=record["receiptHandle"],
                        VisibilityTimeout=max(1, int(delay)),
                    )
            except Exception as e:
                logger.warning("[%s] Could not set backoff delay: %s", ingest_str, e)
            failures.append({"itemIdentifier": message_id})

        elif decision.action == Action.DEAD_LETTER:
            failure_type = decision.failure_type or "unknown_failure"
            logger.error("[%s] Routing to DLQ (failure_type=%s, retries=%d). Reason: %s",
                         ingest_str, failure_type, retry_count, result.reason)
            try:
                _send_to_dlq(sqs, body, failure_type, result.reason, retry_count)
            except Exception as e:
                logger.error("[%s] Failed to send to DLQ (%s); message will be redelivered", ingest_str, e)
                failures.append({"itemIdentifier": message_id})
                continue

            if result.ingest_id:
                try:
                    if failure_type == "invalid_message":
                        msg = f"Invalid message: {result.reason or 'malformed payload'}"
                    else:
                        msg = f"Processing failed after {retry_count} retry attempts: {result.reason or 'retries exhausted'}"
                    repo.mark_failed(result.ingest_id, msg)
                except Exception as e:
                    logger.warning("[%s] Best-effort mark_failed failed: %s", ingest_str, e)

    return {"batchItemFailures": failures}
