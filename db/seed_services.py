"""
Seeds realistic microservice log data through the complete pipeline:
1. Uploads runtime log files for all 6 microservices to MinIO/S3.
2. Registers initial 'pending' records in MongoDB.
3. Publishes persistent jobs to RabbitMQ 'log-ingestion-queue'.
4. Monitors MongoDB until the worker completes processing all jobs.
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
import boto3
from botocore.client import Config
from dotenv import load_dotenv
import pika
import pymongo

load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "log_analytics")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "ingestions")

# S3 / MinIO Configuration
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "raw-logs")
S3_REGION = os.getenv("S3_REGION", "us-east-1")

# RabbitMQ Configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_QUEUE_NAME = os.getenv("RABBITMQ_QUEUE_NAME", "log-ingestion-queue")

# Services to seed
SERVICE_FILES = [
    ("api-gateway", "api-gateway.jsonl", "dev"),
    ("audit-service", "audit-service.jsonl", "dev"),
    ("auth-service", "auth-service.jsonl", "dev"),
    ("course-service", "course-service.jsonl", "dev"),
    ("service-registry", "service-registry.jsonl", "dev"),
    ("student-service", "student-service.jsonl", "dev"),
]


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket(s3_client):
    try:
        s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
    except Exception:
        s3_client.create_bucket(Bucket=S3_BUCKET_NAME)
        print(f"[+] Created MinIO bucket '{S3_BUCKET_NAME}'.")


def seed_services():
    print("=" * 65)
    print(" Pipeline Test Data Seeder (6 Microservices)")
    print("=" * 65)

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    runtime_logs_dir = os.path.join(base_dir, "runtime-logs")

    if not os.path.isdir(runtime_logs_dir):
        print(f"[-] ERROR: runtime-logs directory not found at: {runtime_logs_dir}")
        return

    # 1. Connect to MinIO
    s3_client = get_s3_client()
    ensure_bucket(s3_client)

    # 2. Connect to MongoDB
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    collection = mongo_client[MONGO_DB_NAME][MONGO_COLLECTION]

    # 3. Connect to RabbitMQ
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
    )
    rmq_conn = pika.BlockingConnection(parameters)
    channel = rmq_conn.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE_NAME, durable=True)

    seeded_records = []

    print("[1] Uploading log files, creating pending records & queueing jobs:\n")

    for service_name, filename, env in SERVICE_FILES:
        file_path = os.path.join(runtime_logs_dir, filename)
        if not os.path.isfile(file_path):
            print(f"    [-] Skipping {service_name}: file {filename} not found.")
            continue

        ingest_id = str(uuid.uuid4())
        object_key = f"raw-logs/{service_name}-{ingest_id}.jsonl"

        # a. Upload to MinIO
        s3_client.upload_file(file_path, S3_BUCKET_NAME, object_key)

        # b. Insert into MongoDB
        record = {
            "ingest_id": ingest_id,
            "service_name": service_name,
            "environment": env,
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
        collection.insert_one(record)

        # c. Publish to RabbitMQ
        payload = {
            "ingest_id": ingest_id,
            "service_name": service_name,
            "object_key": object_key,
        }
        channel.basic_publish(
            exchange="",
            routing_key=RABBITMQ_QUEUE_NAME,
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent
            ),
        )

        seeded_records.append((service_name, ingest_id))
        print(f"    [+] Queued: {service_name.ljust(18)} (ingest_id: {ingest_id[:8]}...)")

    rmq_conn.close()

    print(f"\n[2] All {len(seeded_records)} jobs published to RabbitMQ queue '{RABBITMQ_QUEUE_NAME}'.")
    print("\n[3] Waiting for Log Worker to process jobs...")
    print("    (Ensure your worker is running in another CMD: cd log-worker && python worker.py)\n")

    # 4. Poll MongoDB for completion
    all_completed = False
    for attempt in range(1, 21):
        time.sleep(1.5)
        completed_count = collection.count_documents({
            "ingest_id": {"$in": [r[1] for r in seeded_records]},
            "status": {"$in": ["completed", "failed"]},
        })

        print(f"    * Progress: {completed_count}/{len(seeded_records)} jobs processed...", end="\r")
        if completed_count == len(seeded_records):
            all_completed = True
            break

    print()
    if all_completed:
        print("\n[OK] All microservice jobs processed by the worker!")
    else:
        print("\n[!] Some jobs are still pending in the queue. They will process as soon as the worker runs.")

    # 5. Display summary table of seeded records
    print("\n" + "=" * 65)
    print(" Ingested Microservice Records Status")
    print("=" * 65)
    print(f"{'Service':<18} {'Status':<10} {'Logs':<6} {'Errors':<7} {'Health':<10} {'Ingest ID':<12}")
    print("-" * 65)

    for service_name, ingest_id in seeded_records:
        doc = collection.find_one({"ingest_id": ingest_id})
        status = doc.get("status", "unknown") if doc else "missing"
        metrics = (doc or {}).get("metrics") or {}
        report = (doc or {}).get("report") or {}

        logs = str(metrics.get("total_logs", "-"))
        errors = str(metrics.get("error_count", "-"))
        health = str(report.get("health", "-"))

        print(f"{service_name:<18} {status:<10} {logs:<6} {errors:<7} {health:<10} {ingest_id[:8]}...")

    print("=" * 65 + "\n")


if __name__ == "__main__":
    seed_services()
