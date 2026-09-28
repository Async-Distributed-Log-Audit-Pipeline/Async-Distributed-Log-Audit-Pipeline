from datetime import datetime, timezone
import logging
from typing import Any
import pika

logger = logging.getLogger(__name__)


def get_retry_count(properties: Any) -> int:
    """
    Extracts the 'retry_count' header from pika message properties.
    Returns 0 if headers are missing or if key is absent.
    """
    if not properties or not hasattr(properties, "headers") or not properties.headers:
        return 0

    count = properties.headers.get("retry_count", 0)
    try:
        return int(count)
    except (ValueError, TypeError):
        return 0


def setup_rabbitmq_channel(channel: Any, dlq_name: str) -> None:
    """
    Configures RabbitMQ channel:
    - Declares the durable Dead Letter Queue (DLQ).
    - Enables publisher confirmations (confirm_delivery) so failed publishes raise an exception.
    """
    channel.queue_declare(queue=dlq_name, durable=True)
    channel.confirm_delivery()


def publish_retry(channel: Any, queue_name: str, body: bytes, properties: Any, retry_count: int) -> None:
    """
    Republishes the message body back to the main queue with updated retry_count header.
    Message is published as persistent (delivery_mode=2).
    """
    headers = dict(properties.headers) if (properties and getattr(properties, "headers", None)) else {}
    headers["retry_count"] = retry_count

    content_type = getattr(properties, "content_type", None) or "application/json"

    new_props = pika.BasicProperties(
        delivery_mode=2,  # Persistent message
        content_type=content_type,
        headers=headers,
    )

    channel.basic_publish(
        exchange="",
        routing_key=queue_name,
        body=body,
        properties=new_props,
    )


def publish_dlq(
    channel: Any,
    dlq_name: str,
    body: bytes,
    properties: Any,
    failure_type: str,
    reason: str | None,
    retry_count: int,
    worker_id: str,
) -> None:
    """
    Publishes the original unchanged message body to the Dead Letter Queue (DLQ).
    Attaches diagnostic headers: failure_type, failure_reason, retry_count, failed_at, worker_id.
    """
    headers = dict(properties.headers) if (properties and getattr(properties, "headers", None)) else {}
    headers.update({
        "failure_type": failure_type,
        "failure_reason": str(reason) if reason else "Unknown reason",
        "retry_count": retry_count,
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "worker_id": worker_id,
    })

    content_type = getattr(properties, "content_type", None) or "application/json"

    new_props = pika.BasicProperties(
        delivery_mode=2,  # Persistent message
        content_type=content_type,
        headers=headers,
    )

    channel.basic_publish(
        exchange="",
        routing_key=dlq_name,
        body=body,
        properties=new_props,
    )
