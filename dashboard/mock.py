"""Mock data generator and demo state provider for pipeline testing without backend."""
import json
import time
import uuid
from datetime import datetime, timezone, timedelta

# Realistic error templates for demo simulation
DEMO_ERROR_SAMPLES = [
    ("product-service", "NullPointerException in ProductMapper line 84"),
    ("coupon-service", "ConnectionTimeoutException: Coupon DB unresponsive"),
    ("api-gateway", "502 Bad Gateway from upstream product-service"),
    ("auth-service", "SignatureVerificationException: JWT secret key rotated"),
]


def init_demo_state(session_state) -> None:
    """Seed session state with realistic demo ingestions for initial viva presentation."""
    session_state.setdefault("demo_created", {})
    session_state.setdefault("demo_meta", {})

    if "ingestions" not in session_state or not session_state["ingestions"]:
        now = datetime.now(timezone.utc)
        completed_id = str(uuid.uuid4())
        failed_id = str(uuid.uuid4())
        processing_id = str(uuid.uuid4())

        # Record demo metadata
        session_state["demo_created"][completed_id] = time.time() - 300
        session_state["demo_created"][failed_id] = time.time() - 180
        session_state["demo_created"][processing_id] = time.time() - 6  # currently in processing

        session_state["demo_meta"][completed_id] = {
            "status": "completed",
            "service_name": "product-service",
            "environment": "prod",
            "created_at": (now - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "processed_at": (now - timedelta(minutes=4, seconds=52)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "metrics": {
                "total_logs": 14250,
                "error_count": 48,
                "warning_count": 210,
                "critical_count": 4,
            },
            "top_error": "NullPointerException in ProductMapper line 84",
            "error_reason": None,
        }

        session_state["demo_meta"][failed_id] = {
            "status": "failed",
            "service_name": "coupon-service",
            "environment": "staging",
            "created_at": (now - timedelta(minutes=3)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "processed_at": (now - timedelta(minutes=2, seconds=45)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "metrics": {
                "total_logs": 240,
                "error_count": 14,
                "warning_count": 5,
                "critical_count": 8,
            },
            "top_error": "Broker DLQ timeout: consumer worker unacknowledged",
            "error_reason": "Worker exceeded retry count (3/3): Dead Letter Queue reached",
        }

        session_state["demo_meta"][processing_id] = {
            "status": "processing",
            "service_name": "api-gateway",
            "environment": "prod",
            "created_at": (now - timedelta(seconds=6)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "processed_at": None,
            "metrics": None,
            "top_error": None,
            "error_reason": None,
        }

        session_state["ingestions"] = [
            {
                "ingest_id": processing_id,
                "service_name": "api-gateway",
                "environment": "prod",
                "submitted_at": (now - timedelta(seconds=6)).strftime("%H:%M:%S"),
            },
            {
                "ingest_id": failed_id,
                "service_name": "coupon-service",
                "environment": "staging",
                "submitted_at": (now - timedelta(minutes=3)).strftime("%H:%M:%S"),
            },
            {
                "ingest_id": completed_id,
                "service_name": "product-service",
                "environment": "prod",
                "submitted_at": (now - timedelta(minutes=5)).strftime("%H:%M:%S"),
            },
        ]


def mock_upload(file, service_name: str, environment: str, session_state) -> dict:
    """Generate mock upload response and register timestamp."""
    ingest_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    session_state.setdefault("demo_created", {})[ingest_id] = time.time()
    session_state.setdefault("demo_meta", {})[ingest_id] = {
        "service_name": service_name,
        "environment": environment,
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
    }
    return {"ingest_id": ingest_id, "status": "pending"}


def mock_status(ingest_id: str, session_state) -> dict:
    """Simulate ingestion lifecycle: pending (<4s) -> processing (<9s) -> completed (>9s)."""
    # Check if this ID has explicit demo metadata
    demo_meta = session_state.get("demo_meta", {}).get(ingest_id)
    if demo_meta and "status" in demo_meta and demo_meta["status"] in ("failed", "completed"):
        rec = {
            "ingest_id": ingest_id,
            "service_name": demo_meta.get("service_name", "unknown-service"),
            "status": demo_meta["status"],
            "metrics": demo_meta.get("metrics"),
            "top_error": demo_meta.get("top_error"),
            "error_reason": demo_meta.get("error_reason"),
            "created_at": demo_meta.get("created_at"),
            "processed_at": demo_meta.get("processed_at"),
        }
        return rec

    # Calculate status based on elapsed time
    demo_created = session_state.setdefault("demo_created", {})
    created_time = demo_created.setdefault(ingest_id, time.time())
    age = time.time() - created_time

    if age < 4:
        status = "pending"
    elif age < 9:
        status = "processing"
    else:
        status = "completed"

    rec = {
        "ingest_id": ingest_id,
        "service_name": demo_meta.get("service_name", "service-demo") if demo_meta else "service-demo",
        "status": status,
        "metrics": None,
        "top_error": None,
        "error_reason": None,
        "created_at": demo_meta.get("created_at", datetime.fromtimestamp(created_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")),
        "processed_at": None,
    }

    if status == "completed":
        rec["metrics"] = {
            "total_logs": 12500,
            "error_count": 42,
            "warning_count": 180,
            "critical_count": 3,
        }
        rec["top_error"] = "NullPointerException in ProductMapper line 84"
        rec["processed_at"] = datetime.fromtimestamp(created_time + 9, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return rec


def mock_summary() -> list[dict]:
    """Provide realistic mock metrics summary for viva presentation."""
    return [
        {
            "service_name": "product-service",
            "total_logs": 19420,
            "error_count": 84,
            "warning_count": 312,
            "critical_count": 6,
            "health": "critical",
            "top_error": "NullPointerException in ProductMapper line 84",
        },
        {
            "service_name": "coupon-service",
            "total_logs": 13850,
            "error_count": 42,
            "warning_count": 185,
            "critical_count": 0,
            "health": "degraded",
            "top_error": "ConnectionTimeoutException: Coupon DB pool latency > 500ms",
        },
        {
            "service_name": "api-gateway",
            "total_logs": 42800,
            "error_count": 21,
            "warning_count": 430,
            "critical_count": 0,
            "health": "healthy",
            "top_error": "502 Bad Gateway upstream timeout",
        },
        {
            "service_name": "auth-service",
            "total_logs": 18100,
            "error_count": 8,
            "warning_count": 94,
            "critical_count": 0,
            "health": "healthy",
            "top_error": "JWT signature verification expired",
        },
    ]


def generate_sample_logs() -> str:
    """Generate a clean, valid sample JSONL log file for demonstration."""
    sample_records = [
        {"timestamp": "2026-09-29T08:00:01Z", "level": "INFO", "service": "api-gateway", "message": "GET /api/v1/health HTTP/1.1 200 OK 4ms"},
        {"timestamp": "2026-09-29T08:00:03Z", "level": "INFO", "service": "product-service", "message": "Fetching catalog item SKU-88401 from cache"},
        {"timestamp": "2026-09-29T08:00:05Z", "level": "WARN", "service": "coupon-service", "message": "Cache miss for coupon code FLASH50; querying PostgreSQL"},
        {"timestamp": "2026-09-29T08:00:07Z", "level": "INFO", "service": "auth-service", "message": "Token validated for user_id=usr_90214"},
        {"timestamp": "2026-09-29T08:00:09Z", "level": "ERROR", "service": "product-service", "message": "NullPointerException in ProductMapper line 84: SKU not found"},
        {"timestamp": "2026-09-29T08:00:11Z", "level": "INFO", "service": "api-gateway", "message": "POST /api/v1/cart HTTP/1.1 201 Created 18ms"},
        {"timestamp": "2026-09-29T08:00:14Z", "level": "WARN", "service": "coupon-service", "message": "Connection pool usage at 85% capacity (42/50 connections active)"},
        {"timestamp": "2026-09-29T08:00:17Z", "level": "CRITICAL", "service": "coupon-service", "message": "ConnectionTimeoutException: Coupon DB pool latency > 500ms"},
        {"timestamp": "2026-09-29T08:00:20Z", "level": "INFO", "service": "product-service", "message": "Rebuilding local in-memory cache for department electronics"},
        {"timestamp": "2026-09-29T08:00:22Z", "level": "INFO", "service": "api-gateway", "message": "GET /api/v1/inventory HTTP/1.1 200 OK 12ms"},
        {"timestamp": "2026-09-29T08:00:24Z", "level": "WARN", "service": "auth-service", "message": "Multiple failed authentication attempts detected for IP 192.168.1.104"},
        {"timestamp": "2026-09-29T08:00:27Z", "level": "ERROR", "service": "api-gateway", "message": "502 Bad Gateway upstream socket timeout after 5000ms"},
        {"timestamp": "2026-09-29T08:00:30Z", "level": "INFO", "service": "product-service", "message": "Inventory stock check successful for item SKU-1192"},
        {"timestamp": "2026-09-29T08:00:33Z", "level": "INFO", "service": "auth-service", "message": "Session token refreshed for user_id=usr_10442"},
        {"timestamp": "2026-09-29T08:00:35Z", "level": "CRITICAL", "service": "product-service", "message": "Circuit breaker OPEN for inventory-backend (failure rate: 64%)"},
        {"timestamp": "2026-09-29T08:00:38Z", "level": "WARN", "service": "api-gateway", "message": "Rate limit threshold approached (89% quota) for client API-Key-091"},
        {"timestamp": "2026-09-29T08:00:41Z", "level": "INFO", "service": "coupon-service", "message": "Applied promo code AUTUMN20 to cart cart_77215"},
        {"timestamp": "2026-09-29T08:00:44Z", "level": "ERROR", "service": "auth-service", "message": "JWT signature verification expired: clock skew exceeded"},
        {"timestamp": "2026-09-29T08:00:47Z", "level": "INFO", "service": "api-gateway", "message": "GET /api/v1/orders HTTP/1.1 200 OK 24ms"},
        {"timestamp": "2026-09-29T08:00:50Z", "level": "INFO", "service": "product-service", "message": "Batch product sync completed successfully: 450 items updated"},
    ]
    return "\n".join(json.dumps(record) for record in sample_records)
