"""
Amazon SQS queue client: publishes log-ingestion jobs for the worker Lambda.
"""

import json
import logging
from functools import lru_cache
from typing import Any, Dict

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class QueueUnavailableError(Exception):
    """Raised when publishing to SQS fails."""


class QueueClient:
    def __init__(self, queue_url: str, region: str = "us-east-1"):
        self.queue_url = queue_url
        self.sqs = boto3.client("sqs", region_name=region)

    def publish_job(self, payload: Dict[str, Any]) -> None:
        """Send one job message. SQS returns a MessageId only once the message is durably stored."""
        try:
            resp = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(payload),
            )
            logger.info("Published job '%s' to SQS (MessageId=%s).", payload.get("ingest_id"), resp.get("MessageId"))
        except (ClientError, BotoCoreError, Exception) as e:
            logger.error("Failed to publish message to SQS: %s", e)
            raise QueueUnavailableError(f"SQS publishing error: {e}") from e


@lru_cache(maxsize=4)
def _build_queue_client(queue_url: str, region: str) -> QueueClient:
    # Cached so warm Lambda invocations reuse the boto3 client (saves ~100 ms per request).
    return QueueClient(queue_url=queue_url, region=region)


def get_queue_client(settings: Settings = Depends(get_settings)) -> QueueClient:
    return _build_queue_client(settings.SQS_QUEUE_URL, settings.AWS_REGION)
