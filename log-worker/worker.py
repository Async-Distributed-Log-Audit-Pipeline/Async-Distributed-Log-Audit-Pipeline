import os
import time
import pika
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_QUEUE_NAME = os.getenv("RABBITMQ_QUEUE_NAME", "log-ingestion-queue")


def callback(ch, method, properties, body):
    print(f"[x] Received raw message: {body.decode('utf-8', errors='replace')}", flush=True)

    # TODO Phase 2: parse message and fetch file from storage
    # TODO Phase 3: parse log file
    # TODO Phase 4: write results to MongoDB

    # Manually acknowledge the message
    ch.basic_ack(delivery_tag=method.delivery_tag)


def connect_with_retry():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
    )

    retry_delay = 5  # seconds
    while True:
        try:
            print(f"Connecting to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}...", flush=True)
            connection = pika.BlockingConnection(parameters)
            print("Connected to RabbitMQ successfully.", flush=True)
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            print(f"RabbitMQ connection failed ({e}). Retrying in {retry_delay} seconds...", flush=True)
            time.sleep(retry_delay)


def main():
    connection = connect_with_retry()
    channel = connection.channel()

    # Declare durable queue
    channel.queue_declare(queue=RABBITMQ_QUEUE_NAME, durable=True)

    print(f" [*] Waiting for messages in queue '{RABBITMQ_QUEUE_NAME}'. To exit press CTRL+C", flush=True)

    # Set up consumer
    channel.basic_consume(
        queue=RABBITMQ_QUEUE_NAME,
        on_message_callback=callback,
        auto_ack=False,
    )

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\nWorker stopped by user.", flush=True)
        try:
            connection.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()