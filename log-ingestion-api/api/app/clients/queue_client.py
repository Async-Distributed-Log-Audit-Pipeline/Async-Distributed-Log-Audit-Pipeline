import json
import logging
from typing import Any, Dict, Optional
from fastapi import Depends
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import pika
from pika.exceptions import AMQPConnectionError, AMQPError

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class QueueUnavailableError(Exception):
    """Raised when publishing to RabbitMQ or AWS SQS fails due to connectivity or broker errors."""
    pass


class QueueClient:
    """
    Unified message publisher supporting both RabbitMQ and AWS SQS.
    Dispatches log ingestion jobs seamlessly based on queue_type.
    """

    def __init__(
        self,
        queue_type: str = "rabbitmq",
        host: str = "localhost",
        port: int = 5672,
        user: str = "guest",
        password: str = "guest",
        queue_name: str = "log-ingestion-queue",
        sqs_queue_url: Optional[str] = None,
        region: str = "us-east-1",
    ):
        self.queue_type = queue_type.lower()
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.queue_name = queue_name
        self.sqs_queue_url = sqs_queue_url
        self.region = region

        if self.queue_type == "sqs":
            try:
                self.sqs_client = boto3.client("sqs", region_name=self.region)
            except Exception as e:
                logger.error("Failed to initialize AWS SQS client: %s", e)
                raise QueueUnavailableError(f"SQS client initialization error: {e}") from e

    def publish_job(self, payload: Dict[str, Any]) -> None:
        """
        Publishes a log ingestion job message to either AWS SQS or RabbitMQ.
        """
        if self.queue_type == "sqs":
            self._publish_sqs(payload)
        else:
            self._publish_rabbitmq(payload)

    def _publish_sqs(self, payload: Dict[str, Any]) -> None:
        if not self.sqs_queue_url:
            raise QueueUnavailableError("SQS_QUEUE_URL is not configured.")

        try:
            message_body = json.dumps(payload)
            response = self.sqs_client.send_message(
                QueueUrl=self.sqs_queue_url,
                MessageBody=message_body,
            )
            logger.info(
                "Published job '%s' to AWS SQS (MessageId: %s).",
                payload.get("ingest_id"),
                response.get("MessageId"),
            )
        except (ClientError, BotoCoreError, Exception) as e:
            logger.error("Failed to send message to AWS SQS: %s", e)
            raise QueueUnavailableError(f"AWS SQS publishing error: {e}") from e

    def _publish_rabbitmq(self, payload: Dict[str, Any]) -> None:
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

            channel.queue_declare(queue=self.queue_name, durable=True)
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
        queue_type=settings.QUEUE_TYPE,
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
        user=settings.RABBITMQ_USER,
        password=settings.RABBITMQ_PASSWORD,
        queue_name=settings.RABBITMQ_QUEUE_NAME,
        sqs_queue_url=settings.SQS_QUEUE_URL,
        region=settings.S3_REGION,
    )
