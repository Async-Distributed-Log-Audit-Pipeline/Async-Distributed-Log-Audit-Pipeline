"""
RabbitMQ Queue Client for dispatching log ingestion jobs.
Publishes persistent messages to the default exchange with routing key set to the target queue.
"""

import json
import logging
from typing import Any, Dict
from fastapi import Depends
import pika
from pika.exceptions import AMQPConnectionError, AMQPError

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class QueueUnavailableError(Exception):
    """Raised when publishing to RabbitMQ fails due to connectivity or broker errors."""
    pass


class QueueClient:
    """
    Thread-safe RabbitMQ message publisher.
    Opens a short-lived connection/channel per publish operation with publisher confirms enabled.
    This design avoids thread-safety issues with pika (which is not thread-safe) and ensures
    delivery is confirmed by the broker before returning.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        user: str = "guest",
        password: str = "guest",
        queue_name: str = "log-ingestion-queue",
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.queue_name = queue_name

    def publish_job(self, payload: Dict[str, Any]) -> None:
        """
        Publishes a log ingestion job message to RabbitMQ.
        Declares the target queue as durable (matching worker declaration),
        enables publisher confirms, and publishes with DeliveryMode.Persistent.
        """
        credentials = pika.PlainCredentials(self.user, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=credentials,
            connection_attempts=2,
            retry_delay=1,
            socket_timeout=5,
        )

        connection = None
        try:
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            # Declare durable queue matching the worker's configuration exactly
            channel.queue_declare(queue=self.queue_name, durable=True)

            # Enable publisher confirms so publish errors raise exceptions
            channel.confirm_delivery()

            message_body = json.dumps(payload).encode("utf-8")

            channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=pika.DeliveryMode.Persistent,
                    content_type="application/json",
                ),
                mandatory=True,
            )
            logger.info("Published job '%s' to RabbitMQ queue '%s'.", payload.get("ingest_id"), self.queue_name)

        except (AMQPConnectionError, AMQPError, Exception) as e:
            logger.error("Failed to publish message to RabbitMQ: %s", e)
            raise QueueUnavailableError(f"RabbitMQ publishing error: {e}") from e
        finally:
            if connection and connection.is_open:
                try:
                    connection.close()
                except Exception:
                    pass


def get_queue_client(
    settings: Settings = Depends(get_settings),
) -> QueueClient:
    """FastAPI dependency provider for QueueClient."""
    return QueueClient(
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
        user=settings.RABBITMQ_USER,
        password=settings.RABBITMQ_PASSWORD,
        queue_name=settings.RABBITMQ_QUEUE_NAME,
    )
