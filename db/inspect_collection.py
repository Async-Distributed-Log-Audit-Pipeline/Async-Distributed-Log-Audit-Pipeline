"""
Inspects the existing 'ingestions' MongoDB collection and prints:
1. Connection status and collection document count.
2. Status distribution across existing records.
3. Inferred schema / field data types.
4. Detailed breakdown of a sample completed record.
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
import pymongo
from pymongo.errors import ConnectionFailure, PyMongoError

# Load environment variables from .env file if present
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "log_analytics")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "ingestions")


def format_value_for_display(val):
    """Helper to format dates and complex types for pretty-printing."""
    if isinstance(val, datetime):
        return val.isoformat()
    return val


def inspect_collection():
    print("=" * 65)
    print(" MongoDB Ingestions Collection Inspector")
    print("=" * 65)
    print(f"Connecting to: {MONGO_URI}")
    print(f"Database:      {MONGO_DB_NAME}")
    print(f"Collection:    {MONGO_COLLECTION}\n")

    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Verify connection
        client.admin.command("ping")
        print("[+] Successfully connected to MongoDB server.")
    except ConnectionFailure as e:
        print(f"[-] ERROR: Could not connect to MongoDB: {e}")
        print("    Ensure Docker container 'log-worker-mongodb' is running.")
        return

    db = client[MONGO_DB_NAME]
    collection = db[MONGO_COLLECTION]

    total_docs = collection.count_documents({})
    print(f"[+] Total documents in '{MONGO_COLLECTION}': {total_docs}\n")

    if total_docs == 0:
        print("[!] The collection is empty. Run a worker ingestion job first.")
        return

    # 1. Status breakdown
    print("--- Document Status Breakdown ---")
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    status_counts = list(collection.aggregate(pipeline))
    for row in status_counts:
        print(f"  * Status '{row['_id']}': {row['count']} record(s)")
    print()

    # 2. Existing indexes
    print("--- Existing Collection Indexes ---")
    indexes = collection.list_indexes()
    for idx in indexes:
        print(f"  * Index: {idx['name']} -> Keys: {idx['key']}")
    print()

    # 3. Field inspection from sample documents
    print("--- Document Schema & Field Types ---")
    fields_seen = {}
    for doc in collection.find().limit(10):
        for k, v in doc.items():
            t_name = type(v).__name__
            if k not in fields_seen:
                fields_seen[k] = set()
            fields_seen[k].add(t_name)

    for field, types in sorted(fields_seen.items()):
        type_str = ", ".join(sorted(types))
        print(f"  * {field.ljust(24)} : {type_str}")
    print()

    # 4. Sample record preview
    sample_completed = collection.find_one({"status": "completed"})
    sample = sample_completed or collection.find_one()

    if sample:
        print("--- Sample Document Preview ---")
        print(f"  * _id:                   {sample.get('_id')}")
        print(f"  * ingest_id:             {sample.get('ingest_id')}")
        print(f"  * service_name:          {sample.get('service_name')}")
        print(f"  * environment:           {sample.get('environment')}")
        print(f"  * object_key:            {sample.get('object_key')}")
        print(f"  * status:                {sample.get('status')}")
        print(f"  * created_at:            {sample.get('created_at')}")
        print(f"  * processing_started_at: {sample.get('processing_started_at')}")
        print(f"  * processed_at:          {sample.get('processed_at')}")
        print(f"  * error_reason:          {sample.get('error_reason')}")
        print(f"  * top_error:             {sample.get('top_error')}")

        metrics = sample.get("metrics")
        if metrics:
            print(f"  * metrics:               {json.dumps(metrics, indent=4)}")

        report = sample.get("report")
        if report:
            print("  * report:")
            print(f"      - health:        {report.get('health')}")
            print(f"      - time_range:    {report.get('time_range')}")
            print(f"      - skipped_lines: {report.get('skipped_lines')}")
            print(f"      - top_errors:    {len(report.get('top_errors', []))} items")
            print(f"      - top_warnings:  {len(report.get('top_warnings', []))} items")
            print(f"      - top_sources:   {len(report.get('top_sources', []))} items")
            print(f"      - error_samples: {len(report.get('error_samples', []))} items")
            print(f"      - findings:      {len(report.get('findings', []))} items")

    print("\n" + "=" * 65)
    print(" Inspection complete.")
    print("=" * 65)


if __name__ == "__main__":
    inspect_collection()
