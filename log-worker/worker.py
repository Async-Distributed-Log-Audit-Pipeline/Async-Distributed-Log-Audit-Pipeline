import logging
import os
import signal
import socket
import sys
import time
import pika
from dotenv import load_dotenv

from messaging import get_retry_count, publish_dlq, publish_retry, setup_rabbitmq_channel
from processor import Outcome, ProcessResult, process_message
from repository.ingestion_repository import IngestionRepository
from retry_policy import Action, compute_delay, decide_action
from storage.storage_client import ObjectStorageClient

load_dotenv()

WORKER_ID = os.getenv("WORKER_ID", os.getenv("COMPUTERNAME", socket.gethostname()))
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_QUEUE_NAME = os.getenv("RABBITMQ_QUEUE_NAME", "log-ingestion-queue")
RABBITMQ_DLQ_NAME = os.getenv("RABBITMQ_DLQ_NAME", "log-ingestion-dlq")
RABBITMQ_HEARTBEAT = int(os.getenv("RABBITMQ_HEARTBEAT", "600"))
PREFETCH_COUNT = int(os.getenv("PREFETCH_COUNT", "1"))

# App-level retry configuration
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BASE_DELAY_SECONDS = float(os.getenv("RETRY_BASE_DELAY_SECONDS", "2.0"))
RETRY_MAX_DELAY_SECONDS = float(os.getenv("RETRY_MAX_DELAY_SECONDS", "60.0"))

# Structured logging for terminal output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

stop_requested = False


def signal_handler(signum, frame):
    """
    Handles SIGINT / SIGTERM signals for graceful worker shutdown.
    Ensures current in-flight message completes before exiting.
    """
    global stop_requested
    logger.info("[%s] Shutdown signal received. Finishing in-flight job before exiting...", WORKER_ID)
    stop_requested = True


def connect_to_rabbitmq():
    """
    Establishes connection to RabbitMQ with retry logic and heartbeat configuration.
    """
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=RABBITMQ_HEARTBEAT,
    )

    retry_delay = 5
    while not stop_requested:
        try:
            logger.info("[%s] Connecting to RabbitMQ at %s:%d (heartbeat=%ds)...", WORKER_ID, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_HEARTBEAT)
            connection = pika.BlockingConnection(parameters)
            logger.info("[%s] Successfully connected to RabbitMQ.", WORKER_ID)
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning("[%s] RabbitMQ connection failed: %s. Retrying in %d seconds...", WORKER_ID, e, retry_delay)
            time.sleep(retry_delay)
    return None


def main():
    global stop_requested

    # Register OS signal handlers for graceful exit
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("[%s] Starting Log Analytics Worker Service (Phase 6)...", WORKER_ID)

    repo = IngestionRepository()
    storage = ObjectStorageClient()

    while not stop_requested:
        connection = connect_to_rabbitmq()
        if connection is None or stop_requested:
            break

        try:
            channel = connection.channel()
            # Declare durable main queue matching producer
            channel.queue_declare(queue=RABBITMQ_QUEUE_NAME, durable=True)
            # Set prefetch count for fair queue distribution across workers
            channel.basic_qos(prefetch_count=PREFETCH_COUNT)

            # Declare DLQ and enable publisher confirms (confirm_delivery)
            setup_rabbitmq_channel(channel, RABBITMQ_DLQ_NAME)

            logger.info(
                "[%s] Waiting for messages on '%s' (DLQ: '%s', max_retries=%d). Ctrl+C to exit.",
                WORKER_ID,
                RABBITMQ_QUEUE_NAME,
                RABBITMQ_DLQ_NAME,
                MAX_RETRIES,
            )

            def on_message_callback(ch, method, properties, body):
                retry_count = get_retry_count(properties)
                result = process_message(body, repo, storage)
                decision = decide_action(result, retry_count, MAX_RETRIES)

                ingest_str = result.ingest_id or "NO_ID"

                if decision.action == Action.ACK:
                    try:
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        logger.info("[%s] [%s] Message ACKed (outcome: %s).", WORKER_ID, ingest_str, result.outcome.name)
                    except Exception as ack_err:
                        logger.error("[%s] [%s] Failed to ACK message: %s", WORKER_ID, ingest_str, ack_err)

                elif decision.action == Action.RETRY:
                    new_retry_count = retry_count + 1
                    delay = compute_delay(new_retry_count, base=RETRY_BASE_DELAY_SECONDS, cap=RETRY_MAX_DELAY_SECONDS)
                    logger.warning(
                        "[%s] [%s] Processing failed transiently (attempt %d/%d). Retrying in %.2fs. Reason: %s",
                        WORKER_ID,
                        ingest_str,
                        new_retry_count,
                        MAX_RETRIES,
                        delay,
                        result.reason,
                    )

                    # Sleep in max 0.5s slices so shutdown signals are checked quickly
                    end_time = time.monotonic() + delay
                    while time.monotonic() < end_time:
                        if stop_requested:
                            logger.info("[%s] [%s] Shutdown requested during retry delay. Completing republish & ACK before exit...", WORKER_ID, ingest_str)
                            break
                        time.sleep(min(0.5, end_time - time.monotonic()))

                    try:
                        publish_retry(ch, RABBITMQ_QUEUE_NAME, body, properties, new_retry_count)
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        logger.info("[%s] [%s] Message republished to queue (retry_count=%d) and original ACKed.", WORKER_ID, ingest_str, new_retry_count)
                    except Exception as pub_err:
                        logger.error("[%s] [%s] Failed to publish retry message: %s. NACKing original with requeue=True", WORKER_ID, ingest_str, pub_err)
                        try:
                            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                        except Exception:
                            pass

                elif decision.action == Action.DEAD_LETTER:
                    failure_type = decision.failure_type or "unknown_failure"
                    logger.error(
                        "[%s] [%s] Routing message to DLQ '%s' (failure_type='%s', attempts=%d). Reason: %s",
                        WORKER_ID,
                        ingest_str,
                        RABBITMQ_DLQ_NAME,
                        failure_type,
                        retry_count,
                        result.reason,
                    )

                    try:
                        publish_dlq(
                            ch,
                            RABBITMQ_DLQ_NAME,
                            body,
                            properties,
                            failure_type,
                            result.reason,
                            retry_count,
                            WORKER_ID,
                        )
                    except Exception as dlq_err:
                        logger.error("[%s] [%s] Failed to publish message to DLQ: %s. NACKing original with requeue=True", WORKER_ID, ingest_str, dlq_err)
                        try:
                            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                        except Exception:
                            pass
                        return

                    # Best-effort DB update if ingest_id is known
                    if result.ingest_id:
                        try:
                            if failure_type == "invalid_message":
                                fail_msg = f"Invalid message: {result.reason or 'malformed payload'}"
                            else:
                                fail_msg = f"Processing failed after {retry_count} retry attempts: {result.reason or 'retries exhausted'}"
                            repo.mark_failed(result.ingest_id, fail_msg)
                        except Exception as db_err:
                            logger.warning("[%s] [%s] Best-effort mark_failed in DB failed: %s", WORKER_ID, result.ingest_id, db_err)

                    try:
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        logger.info("[%s] [%s] Original message ACKed after routing to DLQ.", WORKER_ID, ingest_str)
                    except Exception as ack_err:
                        logger.error("[%s] [%s] Failed to ACK message after DLQ publish: %s", WORKER_ID, ingest_str, ack_err)

                if stop_requested:
                    logger.info("[%s] Stop requested. Stopping message consumption...", WORKER_ID)
                    ch.stop_consuming()

            channel.basic_consume(
                queue=RABBITMQ_QUEUE_NAME,
                on_message_callback=on_message_callback,
                auto_ack=False,
            )

            channel.start_consuming()

        except (pika.exceptions.AMQPConnectionError, pika.exceptions.AMQPChannelError) as amqp_err:
            logger.warning("[%s] RabbitMQ connection lost (%s). Reconnecting...", WORKER_ID, amqp_err)
        except Exception as err:
            logger.error("[%s] Unexpected worker error: %s", WORKER_ID, err)
        finally:
            if connection and connection.is_open:
                try:
                    connection.close()
                except Exception:
                    pass

        if not stop_requested:
            logger.info("[%s] Reconnecting loop active. Pausing 3s before reconnecting...", WORKER_ID)
            time.sleep(3)

    logger.info("[%s] Log Worker shutdown complete.", WORKER_ID)


if __name__ == "__main__":
    main()