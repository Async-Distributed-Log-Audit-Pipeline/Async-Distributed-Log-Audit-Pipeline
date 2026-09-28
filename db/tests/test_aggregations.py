"""
Unit and Integration Tests for MongoDB Aggregation Queries and Indexes.

Uses an isolated test collection in MongoDB to verify that:
1. Metrics summary correctly aggregates totals, errors, and health states.
2. Filtering by service name and time window works.
3. Health distribution is computed accurately.
4. Top errors are ranked and limited per service.
5. Operational pipeline status counts reflect document states.
6. Time trends correctly group by time interval.
7. Point lookup returns JSON-serializable dictionaries.
8. Unique and compound performance indexes are present.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
import pytest
import pymongo

# Ensure db directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from aggregations import (
    MONGO_URI,
    MONGO_DB_NAME,
    get_metrics_summary,
    get_health_breakdown,
    get_top_errors_by_service,
    get_pipeline_status_counts,
    get_time_based_trends,
    get_ingestion_status,
)

TEST_COLLECTION_NAME = "test_ingestions_temp"


@pytest.fixture(scope="module")
def mongo_test_db():
    """Provides a clean MongoDB database fixture with an isolated test collection."""
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB_NAME]
    test_col = db[TEST_COLLECTION_NAME]

    # Clean up before testing
    test_col.drop()

    # Seed known test fixtures
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    two_days_ago = now - timedelta(days=2)

    sample_docs = [
        # 1. Completed api-gateway
        {
            "ingest_id": "test-uuid-api-1",
            "service_name": "api-gateway",
            "environment": "dev",
            "object_key": "raw-logs/api-1.jsonl",
            "status": "completed",
            "created_at": now,
            "metrics": {
                "total_logs": 100,
                "critical_count": 0,
                "error_count": 5,
                "warning_count": 10,
                "info_count": 85,
                "debug_count": 0,
                "other_count": 0,
            },
            "top_error": "Connection timeout",
            "report": {
                "health": "degraded",
                "top_errors": [
                    {"message": "Connection timeout", "count": 3},
                    {"message": "NullPointer", "count": 2},
                ],
            },
        },
        # 2. Completed api-gateway (older)
        {
            "ingest_id": "test-uuid-api-2",
            "service_name": "api-gateway",
            "environment": "dev",
            "object_key": "raw-logs/api-2.jsonl",
            "status": "completed",
            "created_at": one_hour_ago,
            "metrics": {
                "total_logs": 50,
                "critical_count": 0,
                "error_count": 1,
                "warning_count": 4,
                "info_count": 45,
                "debug_count": 0,
                "other_count": 0,
            },
            "top_error": "Connection timeout",
            "report": {
                "health": "degraded",
                "top_errors": [
                    {"message": "Connection timeout", "count": 1},
                ],
            },
        },
        # 3. Completed auth-service (healthy)
        {
            "ingest_id": "test-uuid-auth-1",
            "service_name": "auth-service",
            "environment": "dev",
            "object_key": "raw-logs/auth-1.jsonl",
            "status": "completed",
            "created_at": now,
            "metrics": {
                "total_logs": 80,
                "critical_count": 0,
                "error_count": 0,
                "warning_count": 2,
                "info_count": 78,
                "debug_count": 0,
                "other_count": 0,
            },
            "top_error": None,
            "report": {
                "health": "warning",
                "top_errors": [],
            },
        },
        # 4. Old document (2 days ago)
        {
            "ingest_id": "test-uuid-old",
            "service_name": "course-service",
            "environment": "dev",
            "object_key": "raw-logs/course-old.jsonl",
            "status": "completed",
            "created_at": two_days_ago,
            "metrics": {
                "total_logs": 20,
                "critical_count": 1,
                "error_count": 2,
                "warning_count": 0,
                "info_count": 17,
                "debug_count": 0,
                "other_count": 0,
            },
            "top_error": "OutOfMemoryError",
            "report": {
                "health": "critical",
                "top_errors": [{"message": "OutOfMemoryError", "count": 2}],
            },
        },
        # 5. Pending document
        {
            "ingest_id": "test-uuid-pending",
            "service_name": "audit-service",
            "environment": "dev",
            "object_key": "raw-logs/audit-p.jsonl",
            "status": "pending",
            "created_at": now,
            "metrics": None,
            "report": None,
        },
        # 6. Failed document
        {
            "ingest_id": "test-uuid-failed",
            "service_name": "audit-service",
            "environment": "dev",
            "object_key": "raw-logs/audit-f.jsonl",
            "status": "failed",
            "created_at": now,
            "error_reason": "File corrupted",
            "metrics": None,
            "report": None,
        },
    ]

    test_col.insert_many(sample_docs)

    # Monkeypatch collection name in aggregations module for tests
    import aggregations
    original_collection_name = aggregations.MONGO_COLLECTION
    aggregations.MONGO_COLLECTION = TEST_COLLECTION_NAME

    yield db

    # Teardown
    test_col.drop()
    aggregations.MONGO_COLLECTION = original_collection_name
    client.close()


def test_metrics_summary_all_services(mongo_test_db):
    """Verifies that metrics summary groups by service and sums counts correctly."""
    summaries = get_metrics_summary(db=mongo_test_db)
    assert len(summaries) == 3  # api-gateway, auth-service, course-service (completed only)

    # Verify api-gateway aggregated 2 documents
    api_summary = next(s for s in summaries if s["service_name"] == "api-gateway")
    assert api_summary["total_logs"] == 150  # 100 + 50
    assert api_summary["error_count"] == 6    # 5 + 1
    assert api_summary["warning_count"] == 14 # 10 + 4
    assert api_summary["ingestion_count"] == 2
    assert api_summary["latest_health"] == "degraded"


def test_metrics_summary_filter_service(mongo_test_db):
    """Verifies filtering by a single service name."""
    summaries = get_metrics_summary(service_name="auth-service", db=mongo_test_db)
    assert len(summaries) == 1
    assert summaries[0]["service_name"] == "auth-service"
    assert summaries[0]["total_logs"] == 80
    assert summaries[0]["error_count"] == 0


def test_metrics_summary_time_window(mongo_test_db):
    """Verifies time window filtering excludes older records."""
    # 24 hours filter should exclude the document from 2 days ago
    summaries = get_metrics_summary(time_window_hours=24, db=mongo_test_db)
    service_names = [s["service_name"] for s in summaries]
    assert "course-service" not in service_names
    assert "api-gateway" in service_names


def test_health_breakdown(mongo_test_db):
    """Verifies health distribution calculations."""
    health = get_health_breakdown(db=mongo_test_db)
    summary = health["summary"]
    assert summary["degraded"] == 1  # api-gateway
    assert summary["warning"] == 1   # auth-service
    assert summary["critical"] == 1  # course-service
    assert summary["total_services"] == 3


def test_top_errors_by_service(mongo_test_db):
    """Verifies that errors are unwound, summed, and ranked."""
    top_errors = get_top_errors_by_service(limit_per_service=2, db=mongo_test_db)
    api_errs = next(s for s in top_errors if s["service_name"] == "api-gateway")
    # Connection timeout appeared 3 times in doc 1 + 1 time in doc 2 = 4
    timeout_err = next(e for e in api_errs["top_errors"] if e["message"] == "Connection timeout")
    assert timeout_err["count"] == 4


def test_pipeline_status_counts(mongo_test_db):
    """Verifies operational status counts across the pipeline."""
    counts = get_pipeline_status_counts(db=mongo_test_db)
    assert counts["completed"] == 4
    assert counts["pending"] == 1
    assert counts["failed"] == 1
    assert counts["processing"] == 0
    assert counts["total"] == 6


def test_time_based_trends(mongo_test_db):
    """Verifies hourly chronological groupings."""
    trends = get_time_based_trends(interval="hour", limit=10, db=mongo_test_db)
    assert len(trends) >= 2
    # Verify trend structure
    first_bucket = trends[0]
    assert "timestamp" in first_bucket
    assert "total_logs" in first_bucket
    assert "ingestion_count" in first_bucket


def test_get_ingestion_status_found(mongo_test_db):
    """Verifies point lookup returns clean JSON-serializable doc."""
    record = get_ingestion_status("test-uuid-api-1", db=mongo_test_db)
    assert record is not None
    assert record["ingest_id"] == "test-uuid-api-1"
    assert record["status"] == "completed"
    assert isinstance(record["_id"], str)  # ObjectId converted to string


def test_get_ingestion_status_not_found(mongo_test_db):
    """Verifies lookup for non-existent ID returns None."""
    record = get_ingestion_status("non-existent-id", db=mongo_test_db)
    assert record is None


def test_production_indexes_exist():
    """Verifies that required production indexes exist on the primary collection."""
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    col = client[MONGO_DB_NAME]["ingestions"]
    indexes = col.list_indexes()
    index_names = {idx["name"] for idx in indexes}

    assert "idx_ingest_id_unique" in index_names
    assert "idx_service_created" in index_names
    assert "idx_status" in index_names
    assert "idx_created_at" in index_names

    # Check unique flag on ingest_id
    ingest_idx = next(idx for idx in col.list_indexes() if idx["name"] == "idx_ingest_id_unique")
    assert ingest_idx.get("unique") is True
    client.close()
