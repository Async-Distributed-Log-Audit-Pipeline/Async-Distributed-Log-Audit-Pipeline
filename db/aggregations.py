"""
MongoDB Aggregation Queries for Log & Audit Pipeline
Database: log_analytics | Collection: ingestions

This module provides high-performance data layer functions designed for:
1. API Developer: importable functions to power GET /metrics/summary, GET /logs/status, etc.
2. Dashboard Developer: aggregate metrics, health distributions, and time trends for Streamlit.

All functions accept an optional `db` instance (pymongo.database.Database).
If omitted, a default connection is established using .env parameters.
All datetime fields and MongoDB ObjectIds in results are converted to JSON-serializable types.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import pymongo

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "log_analytics")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "ingestions")

_client = None


def get_db():
    """Returns a cached pymongo Database instance."""
    global _client
    if _client is None:
        _client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client[MONGO_DB_NAME]


def _format_datetime(val: Any) -> Any:
    """Helper to convert datetime objects to ISO-8601 strings."""
    if isinstance(val, datetime):
        return val.isoformat()
    return val


def get_metrics_summary(
    service_name: Optional[str] = None,
    time_window_hours: Optional[int] = None,
    db: Optional[pymongo.database.Database] = None,
) -> List[Dict[str, Any]]:
    """
    Powers GET /metrics/summary.
    Aggregates log counts, severity breakdowns, and health status grouped by service.

    Parameters:
        service_name: Optional filter for a specific microservice.
        time_window_hours: Optional time window filter (e.g., last 24 hours).
        db: Optional pymongo Database object.

    Returns:
        List of dicts, sorted alphabetically by service_name:
        [
            {
                "service_name": "api-gateway",
                "total_logs": 117,
                "critical_count": 0,
                "error_count": 1,
                "warning_count": 8,
                "info_count": 108,
                "debug_count": 0,
                "other_count": 0,
                "ingestion_count": 1,
                "latest_health": "degraded",
                "latest_ingest_time": "2026-09-28T16:13:38.072000+00:00"
            },
            ...
        ]
    """
    database = db if db is not None else get_db()
    collection = database[MONGO_COLLECTION]

    match_stage: Dict[str, Any] = {"status": "completed"}
    if service_name:
        match_stage["service_name"] = service_name
    if time_window_hours:
        since = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
        match_stage["created_at"] = {"$gte": since}

    pipeline = [
        {"$match": match_stage},
        # Sort by service and created_at desc so $first captures the most recent record
        {"$sort": {"service_name": 1, "created_at": -1}},
        {
            "$group": {
                "_id": "$service_name",
                "total_logs": {"$sum": {"$ifNull": ["$metrics.total_logs", 0]}},
                "critical_count": {"$sum": {"$ifNull": ["$metrics.critical_count", 0]}},
                "error_count": {"$sum": {"$ifNull": ["$metrics.error_count", 0]}},
                "warning_count": {"$sum": {"$ifNull": ["$metrics.warning_count", 0]}},
                "info_count": {"$sum": {"$ifNull": ["$metrics.info_count", 0]}},
                "debug_count": {"$sum": {"$ifNull": ["$metrics.debug_count", 0]}},
                "other_count": {"$sum": {"$ifNull": ["$metrics.other_count", 0]}},
                "ingestion_count": {"$sum": 1},
                "latest_health": {"$first": "$report.health"},
                "latest_ingest_time": {"$first": "$created_at"},
            }
        },
        {"$sort": {"_id": 1}},
        {
            "$project": {
                "_id": 0,
                "service_name": "$_id",
                "total_logs": 1,
                "critical_count": 1,
                "error_count": 1,
                "warning_count": 1,
                "info_count": 1,
                "debug_count": 1,
                "other_count": 1,
                "ingestion_count": 1,
                "latest_health": {"$ifNull": ["$latest_health", "unknown"]},
                "latest_ingest_time": 1,
            }
        },
    ]

    results = list(collection.aggregate(pipeline))
    for row in results:
        row["latest_ingest_time"] = _format_datetime(row.get("latest_ingest_time"))
    return results


def get_health_breakdown(
    time_window_hours: Optional[int] = None,
    db: Optional[pymongo.database.Database] = None,
) -> Dict[str, Any]:
    """
    Computes overall system health distribution across services.

    Returns:
        {
            "summary": {
                "healthy": 2,
                "warning": 2,
                "degraded": 2,
                "critical": 0,
                "total_services": 6
            },
            "by_service": [
                {"service_name": "api-gateway", "health": "degraded"},
                ...
            ]
        }
    """
    database = db if db is not None else get_db()
    collection = database[MONGO_COLLECTION]

    match_stage: Dict[str, Any] = {"status": "completed"}
    if time_window_hours:
        since = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
        match_stage["created_at"] = {"$gte": since}

    pipeline = [
        {"$match": match_stage},
        {"$sort": {"service_name": 1, "created_at": -1}},
        {
            "$group": {
                "_id": "$service_name",
                "latest_health": {"$first": {"$ifNull": ["$report.health", "unknown"]}},
            }
        },
        {"$sort": {"_id": 1}},
    ]

    services_health = list(collection.aggregate(pipeline))

    summary = {
        "healthy": 0,
        "warning": 0,
        "degraded": 0,
        "critical": 0,
        "unknown": 0,
        "total_services": len(services_health),
    }

    by_service = []
    for item in services_health:
        h = item["latest_health"]
        summary[h] = summary.get(h, 0) + 1
        by_service.append({"service_name": item["_id"], "health": h})

    return {
        "summary": summary,
        "by_service": by_service,
    }


def get_top_errors_by_service(
    limit_per_service: int = 3,
    db: Optional[pymongo.database.Database] = None,
) -> List[Dict[str, Any]]:
    """
    Extracts and ranks top errors grouped by microservice across completed ingestions.

    Returns:
        List of dicts:
        [
            {
                "service_name": "api-gateway",
                "top_errors": [
                    {"message": "DiscoveryClient de-registration failed", "count": 2}
                ]
            },
            ...
        ]
    """
    database = db if db is not None else get_db()
    collection = database[MONGO_COLLECTION]

    pipeline = [
        {"$match": {"status": "completed", "report.top_errors": {"$exists": True, "$ne": []}}},
        {"$unwind": "$report.top_errors"},
        {
            "$group": {
                "_id": {
                    "service_name": "$service_name",
                    "message": "$report.top_errors.message",
                },
                "total_occurrences": {"$sum": "$report.top_errors.count"},
            }
        },
        {"$sort": {"_id.service_name": 1, "total_occurrences": -1}},
        {
            "$group": {
                "_id": "$_id.service_name",
                "top_errors": {
                    "$push": {
                        "message": "$_id.message",
                        "count": "$total_occurrences",
                    }
                },
            }
        },
        {
            "$project": {
                "_id": 0,
                "service_name": "$_id",
                "top_errors": {"$slice": ["$top_errors", limit_per_service]},
            }
        },
        {"$sort": {"service_name": 1}},
    ]

    return list(collection.aggregate(pipeline))


def get_pipeline_status_counts(
    db: Optional[pymongo.database.Database] = None,
) -> Dict[str, int]:
    """
    Returns counts of all ingestions categorized by pipeline status.
    Useful for operational monitoring and health checks.

    Returns:
        {
            "pending": 0,
            "processing": 0,
            "completed": 7,
            "failed": 0,
            "total": 7
        }
    """
    database = db if db is not None else get_db()
    collection = database[MONGO_COLLECTION]

    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]

    counts = {
        "pending": 0,
        "processing": 0,
        "completed": 0,
        "failed": 0,
    }

    for row in collection.aggregate(pipeline):
        st = row["_id"]
        if st in counts:
            counts[st] = row["count"]

    counts["total"] = sum(counts.values())
    return counts


def get_time_based_trends(
    interval: str = "hour",
    limit: int = 24,
    db: Optional[pymongo.database.Database] = None,
) -> List[Dict[str, Any]]:
    """
    Groups completed ingestion metrics by time intervals (hour or day) for charts.

    Parameters:
        interval: 'hour' or 'day' (default: 'hour')
        limit: Max number of interval buckets to return (default: 24)

    Returns:
        List of chronological buckets:
        [
            {
                "timestamp": "2026-09-28T16:00:00+00:00",
                "ingestion_count": 6,
                "total_logs": 636,
                "error_count": 4,
                "warning_count": 36
            }
        ]
    """
    database = db if db is not None else get_db()
    collection = database[MONGO_COLLECTION]

    date_unit = "day" if interval.lower() == "day" else "hour"

    pipeline = [
        {"$match": {"status": "completed", "created_at": {"$ne": None}}},
        {
            "$group": {
                "_id": {
                    "$dateTrunc": {
                        "date": "$created_at",
                        "unit": date_unit,
                    }
                },
                "ingestion_count": {"$sum": 1},
                "total_logs": {"$sum": {"$ifNull": ["$metrics.total_logs", 0]}},
                "error_count": {"$sum": {"$ifNull": ["$metrics.error_count", 0]}},
                "warning_count": {"$sum": {"$ifNull": ["$metrics.warning_count", 0]}},
            }
        },
        {"$sort": {"_id": -1}},
        {"$limit": limit},
        {"$sort": {"_id": 1}},
        {
            "$project": {
                "_id": 0,
                "timestamp": "$_id",
                "ingestion_count": 1,
                "total_logs": 1,
                "error_count": 1,
                "warning_count": 1,
            }
        },
    ]

    results = list(collection.aggregate(pipeline))
    for r in results:
        r["timestamp"] = _format_datetime(r.get("timestamp"))
    return results


def get_ingestion_status(
    ingest_id: str,
    db: Optional[pymongo.database.Database] = None,
) -> Optional[Dict[str, Any]]:
    """
    Point lookup for GET /logs/status?id={ingest_id}.
    Converts MongoDB _id and dates to JSON-safe formats so FastAPI can directly serialize it.

    Returns:
        Document dict if found, None if not found.
    """
    database = db if db is not None else get_db()
    collection = database[MONGO_COLLECTION]

    doc = collection.find_one({"ingest_id": ingest_id})
    if not doc:
        return None

    # Clean document for JSON serialization
    doc["_id"] = str(doc["_id"])
    doc["created_at"] = _format_datetime(doc.get("created_at"))
    doc["processing_started_at"] = _format_datetime(doc.get("processing_started_at"))
    doc["processed_at"] = _format_datetime(doc.get("processed_at"))

    return doc
