"""
Sets up JSON Schema Validation and Performance Indexes for the
'ingestions' collection in MongoDB.

Features:
- Idempotent: can be run repeatedly without duplicating indexes or breaking existing data.
- Enforces data integrity: required fields, enum status check, typed sub-documents.
- Creates indexes:
    1. ingest_id (unique) -> Fast O(1) status lookup for GET /logs/status?id=...
    2. service_name + created_at -> Fast filtering and sorting per service
    3. status -> Fast filtering for active vs completed jobs
    4. created_at -> Fast time-window sorting and range queries for dashboards
"""

import os
from dotenv import load_dotenv
import pymongo
from pymongo.errors import PyMongoError, WriteError

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "log_analytics")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "ingestions")

INGESTION_JSON_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "ingest_id",
            "service_name",
            "environment",
            "object_key",
            "status",
            "created_at",
        ],
        "properties": {
            "_id": {"bsonType": "objectId"},
            "ingest_id": {
                "bsonType": "string",
                "description": "Unique ingestion UUID string - required",
            },
            "service_name": {
                "bsonType": "string",
                "description": "Microservice identifier (e.g., api-gateway, auth-service) - required",
            },
            "environment": {
                "bsonType": "string",
                "description": "Environment name (dev, staging, prod) - required",
            },
            "object_key": {
                "bsonType": "string",
                "description": "Storage path in MinIO/S3 - required",
            },
            "status": {
                "enum": ["pending", "processing", "completed", "failed"],
                "description": "Lifecycle state enum - required",
            },
            "created_at": {
                "bsonType": "date",
                "description": "UTC timestamp when record was registered - required",
            },
            "processing_started_at": {
                "bsonType": ["date", "null"],
                "description": "UTC timestamp when worker started log processing",
            },
            "processed_at": {
                "bsonType": ["date", "null"],
                "description": "UTC timestamp when worker finished processing",
            },
            "error_reason": {
                "bsonType": ["string", "null"],
                "description": "Error details if processing failed permanently",
            },
            "top_error": {
                "bsonType": ["string", "null"],
                "description": "Highest frequency error message, or null",
            },
            "metrics": {
                "bsonType": ["object", "null"],
                "description": "Log level counter metrics",
                "properties": {
                    "total_logs": {"bsonType": ["int", "long", "double"]},
                    "critical_count": {"bsonType": ["int", "long", "double"]},
                    "error_count": {"bsonType": ["int", "long", "double"]},
                    "warning_count": {"bsonType": ["int", "long", "double"]},
                    "info_count": {"bsonType": ["int", "long", "double"]},
                    "debug_count": {"bsonType": ["int", "long", "double"]},
                    "other_count": {"bsonType": ["int", "long", "double"]},
                },
            },
            "report": {
                "bsonType": ["object", "null"],
                "description": "Detailed log analytics summary",
                "properties": {
                    "health": {
                        "enum": ["healthy", "warning", "degraded", "critical"],
                        "description": "Computed health indicator",
                    },
                    "time_range": {"bsonType": "object"},
                    "top_errors": {"bsonType": "array"},
                    "top_warnings": {"bsonType": "array"},
                    "top_sources": {"bsonType": "array"},
                    "error_samples": {"bsonType": "array"},
                    "findings": {"bsonType": "array"},
                    "skipped_lines": {"bsonType": ["int", "long", "double"]},
                },
            },
        },
    }
}


def apply_schema_and_indexes():
    print("=" * 65)
    print(" MongoDB Schema & Index Setup")
    print("=" * 65)
    print(f"Connecting to: {MONGO_URI}")
    print(f"Database:      {MONGO_DB_NAME}")
    print(f"Collection:    {MONGO_COLLECTION}\n")

    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB_NAME]

    # Ensure collection exists before collMod
    if MONGO_COLLECTION not in db.list_collection_names():
        db.create_collection(MONGO_COLLECTION)
        print(f"[+] Created collection '{MONGO_COLLECTION}'.")

    # 1. Apply Schema Validation via collMod
    print("[1] Applying JSON Schema Validation...")
    try:
        db.command({
            "collMod": MONGO_COLLECTION,
            "validator": INGESTION_JSON_SCHEMA,
            "validationLevel": "moderate",
            "validationAction": "error",
        })
        print("    [OK] Collection validator successfully updated.")
    except PyMongoError as e:
        print(f"    [-] Failed to apply validator: {e}")
        return

    # 2. Create Indexes
    collection = db[MONGO_COLLECTION]
    print("\n[2] Creating/Updating Indexes...")

    indexes_to_create = [
        # Fast point lookups for GET /logs/status?id={ingest_id}
        pymongo.IndexModel(
            [("ingest_id", pymongo.ASCENDING)],
            unique=True,
            name="idx_ingest_id_unique",
        ),
        # Per-service chronological queries and aggregations
        pymongo.IndexModel(
            [("service_name", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
            name="idx_service_created",
        ),
        # Filtering by state (pending, processing, completed, failed)
        pymongo.IndexModel(
            [("status", pymongo.ASCENDING)],
            name="idx_status",
        ),
        # System-wide time-range queries and trends
        pymongo.IndexModel(
            [("created_at", pymongo.DESCENDING)],
            name="idx_created_at",
        ),
    ]

    try:
        created = collection.create_indexes(indexes_to_create)
        for idx_name in created:
            print(f"    [OK] Index ready: {idx_name}")
    except PyMongoError as e:
        print(f"    [-] Error creating indexes: {e}")
        return

    # 3. Print verified active indexes
    print("\n[3] Active Indexes in Collection:")
    for idx in collection.list_indexes():
        unique_flag = " (UNIQUE)" if idx.get("unique") else ""
        print(f"    * {idx['name']}: {dict(idx['key'])}{unique_flag}")

    # 4. Verify validation by testing an invalid insert
    print("\n[4] Verifying Schema Validation Enforcement...")
    invalid_doc = {
        "ingest_id": "test-invalid-doc",
        "service_name": "test-service",
        "status": "invalid_status_enum",  # Not in allowed statuses
    }
    try:
        collection.insert_one(invalid_doc)
        print("    [-] ERROR: Invalid document was unexpectedly accepted!")
        collection.delete_one({"ingest_id": "test-invalid-doc"})
    except WriteError as we:
        print(f"    [OK] Validation properly rejected invalid document:")
        print(f"         {we.details.get('errmsg', we)}")

    print("\n" + "=" * 65)
    print(" Schema Validation and Indexes successfully applied!")
    print("=" * 65)


if __name__ == "__main__":
    apply_schema_and_indexes()
