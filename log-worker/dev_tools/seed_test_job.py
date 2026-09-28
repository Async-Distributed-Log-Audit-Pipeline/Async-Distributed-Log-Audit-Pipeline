import argparse
from datetime import datetime, timezone
import gzip
import json
import os
import sys
import tempfile
import uuid
import pika
from dotenv import load_dotenv

# Ensure root log-worker directory is in python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from repository.ingestion_repository import IngestionRepository
from storage.storage_client import ObjectStorageClient

load_dotenv()

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_QUEUE_NAME = os.getenv("RABBITMQ_QUEUE_NAME", "log-ingestion-queue")


def parse_args():
    parser = argparse.ArgumentParser(description="Seed a test log ingestion job into the pipeline.")
    parser.add_argument("file_path", help="Path to local log file to upload")
    parser.add_argument("--service-name", default="api-gateway", help="Name of service (default: api-gateway)")
    parser.add_argument("--environment", default="dev", help="Environment name (default: dev)")
    parser.add_argument("--gzip", action="store_true", help="Compress log file with gzip before upload")
    return parser.parse_args()


def main():
    args = parse_args()

    if not os.path.isfile(args.file_path):
        print(f"[ERROR] Specified log file not found: {args.file_path}", file=sys.stderr)
        sys.exit(1)

    ingest_id = str(uuid.uuid4())
    ext = ".jsonl.gz" if args.gzip else ".jsonl"
    object_key = f"raw-logs/{args.service_name}-{ingest_id}{ext}"

    # 1. Compress file if requested, then upload to Object Storage
    storage_client = ObjectStorageClient()

    if args.gzip:
        print(f"[*] Compressing log file '{args.file_path}'...")
        with tempfile.NamedTemporaryFile(suffix=".gz", delete=False) as tmp_gz:
            tmp_gz_path = tmp_gz.name

        try:
            with open(args.file_path, "rb") as f_in:
                with gzip.open(tmp_gz_path, "wb") as f_out:
                    f_out.writelines(f_in)

            print(f"[*] Uploading compressed file to S3 as '{object_key}'...")
            storage_client.upload_file(tmp_gz_path, object_key)
        finally:
            if os.path.exists(tmp_gz_path):
                os.remove(tmp_gz_path)
    else:
        print(f"[*] Uploading file to S3 as '{object_key}'...")
        storage_client.upload_file(args.file_path, object_key)

    print("    [OK] File uploaded to object storage.")

    # 2. Insert record into MongoDB
    repo = IngestionRepository()
    record = {
        "ingest_id": ingest_id,
        "service_name": args.service_name,
        "environment": args.environment,
        "object_key": object_key,
        "status": "pending",
        "metrics": None,
        "top_error": None,
        "report": None,
        "error_reason": None,
        "created_at": datetime.now(timezone.utc),
        "processed_at": None,
        "processing_started_at": None,
    }

    repo.insert_record(record)
    print(f"    [OK] MongoDB document inserted for ingest_id: '{ingest_id}'.")

    # 3. Publish persistent message to RabbitMQ
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
    )

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    # Must match worker.py queue declaration exactly
    channel.queue_declare(queue=RABBITMQ_QUEUE_NAME, durable=True)

    message_payload = {
        "ingest_id": ingest_id,
        "service_name": args.service_name,
        "object_key": object_key,
    }

    channel.basic_publish(
        exchange="",
        routing_key=RABBITMQ_QUEUE_NAME,
        body=json.dumps(message_payload),
        properties=pika.BasicProperties(
            delivery_mode=pika.DeliveryMode.Persistent
        ),
    )

    connection.close()
    print("    [OK] Message published to RabbitMQ queue.")

    print(f"\n[SUCCESS] Test job seeded successfully! Ingest ID: {ingest_id}")


if __name__ == "__main__":
    main()
