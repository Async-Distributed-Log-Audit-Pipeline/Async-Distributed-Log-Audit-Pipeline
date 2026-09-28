"""
Unit tests for the metrics summary endpoint (/metrics/summary).
Tests aggregation over completed records, date filters, service filters, and operational health rules.
"""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.ingestion_repository import get_ingestion_repository
from tests.fakes.fake_repository import FakeIngestionRepository


@pytest.fixture
def fake_repo():
    return FakeIngestionRepository()


@pytest.fixture
def client_with_repo(client: TestClient, fake_repo: FakeIngestionRepository):
    app.dependency_overrides[get_ingestion_repository] = lambda: fake_repo
    yield client
    app.dependency_overrides.pop(get_ingestion_repository, None)


def test_metrics_summary_empty(client_with_repo: TestClient):
    """Verifies that an empty database yields an empty summary list."""
    response = client_with_repo.get("/metrics/summary")
    assert response.status_code == 200
    assert response.json() == []


def test_metrics_summary_ignores_non_completed(client_with_repo: TestClient, fake_repo: FakeIngestionRepository):
    """Verifies that pending, processing, and failed jobs are not included in summary aggregation."""
    records = [
        {
            "ingest_id": "job-pending",
            "service_name": "gateway",
            "environment": "dev",
            "status": "pending",
            "metrics": {"total_logs": 50, "error_count": 10, "warning_count": 5, "critical_count": 0},
            "created_at": datetime.now(timezone.utc),
            "object_key": "k1",
            "top_error": None,
            "report": None,
            "error_reason": None,
            "processed_at": None,
            "processing_started_at": None,
        },
        {
            "ingest_id": "job-failed",
            "service_name": "gateway",
            "environment": "dev",
            "status": "failed",
            "metrics": None,
            "created_at": datetime.now(timezone.utc),
            "object_key": "k2",
            "top_error": None,
            "report": None,
            "error_reason": "worker crashed",
            "processed_at": None,
            "processing_started_at": None,
        },
    ]
    for r in records:
        fake_repo.insert_record(r)

    response = client_with_repo.get("/metrics/summary")
    assert response.status_code == 200
    assert response.json() == []


def test_metrics_health_rules_and_aggregation(client_with_repo: TestClient, fake_repo: FakeIngestionRepository):
    """
    Verifies metric summing and the three health statuses:
    - critical: critical_count > 0
    - degraded: critical_count == 0 and error_count > 0
    - healthy: critical_count == 0 and error_count == 0
    """
    records = [
        # auth-service: has critical_count > 0 -> critical
        {
            "ingest_id": "auth-1",
            "service_name": "auth-service",
            "status": "completed",
            "metrics": {"total_logs": 200, "error_count": 5, "warning_count": 10, "critical_count": 1},
            "created_at": datetime(2026, 9, 28, 10, 0, 0, tzinfo=timezone.utc),
            "environment": "dev",
            "object_key": "k1",
            "top_error": None,
            "report": None,
            "error_reason": None,
            "processed_at": None,
            "processing_started_at": None,
        },
        # payment-service: error_count > 0, critical_count == 0 -> degraded
        {
            "ingest_id": "pay-1",
            "service_name": "payment-service",
            "status": "completed",
            "metrics": {"total_logs": 100, "error_count": 2, "warning_count": 8, "critical_count": 0},
            "created_at": datetime(2026, 9, 28, 10, 10, 0, tzinfo=timezone.utc),
            "environment": "dev",
            "object_key": "k2",
            "top_error": None,
            "report": None,
            "error_reason": None,
            "processed_at": None,
            "processing_started_at": None,
        },
        # gateway: multiple jobs, no criticals, no errors -> healthy
        {
            "ingest_id": "gw-1",
            "service_name": "gateway",
            "status": "completed",
            "metrics": {"total_logs": 300, "error_count": 0, "warning_count": 15, "critical_count": 0},
            "created_at": datetime(2026, 9, 28, 10, 20, 0, tzinfo=timezone.utc),
            "environment": "dev",
            "object_key": "k3",
            "top_error": None,
            "report": None,
            "error_reason": None,
            "processed_at": None,
            "processing_started_at": None,
        },
        {
            "ingest_id": "gw-2",
            "service_name": "gateway",
            "status": "completed",
            "metrics": {"total_logs": 200, "error_count": 0, "warning_count": 5, "critical_count": 0},
            "created_at": datetime(2026, 9, 28, 10, 25, 0, tzinfo=timezone.utc),
            "environment": "dev",
            "object_key": "k4",
            "top_error": None,
            "report": None,
            "error_reason": None,
            "processed_at": None,
            "processing_started_at": None,
        },
    ]
    for r in records:
        fake_repo.insert_record(r)

    response = client_with_repo.get("/metrics/summary")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    lookup = {item["service_name"]: item for item in data}

    # Verify auth-service (critical)
    assert lookup["auth-service"]["health"] == "critical"
    assert lookup["auth-service"]["critical_count"] == 1
    assert lookup["auth-service"]["total_logs"] == 200

    # Verify payment-service (degraded)
    assert lookup["payment-service"]["health"] == "degraded"
    assert lookup["payment-service"]["error_count"] == 2
    assert lookup["payment-service"]["critical_count"] == 0

    # Verify gateway (healthy, aggregated total_logs = 500, warnings = 20)
    assert lookup["gateway"]["health"] == "healthy"
    assert lookup["gateway"]["total_logs"] == 500
    assert lookup["gateway"]["warning_count"] == 20
    assert lookup["gateway"]["error_count"] == 0
    assert lookup["gateway"]["critical_count"] == 0


def test_metrics_summary_service_filter(client_with_repo: TestClient, fake_repo: FakeIngestionRepository):
    """Verifies that ?service_name=... query filter isolates a single service."""
    t0 = datetime.now(timezone.utc)
    records = [
        {"ingest_id": "1", "service_name": "srv-a", "status": "completed", "metrics": {"total_logs": 10, "error_count": 0, "warning_count": 0, "critical_count": 0}, "created_at": t0, "environment": "dev", "object_key": "k1", "top_error": None, "report": None, "error_reason": None, "processed_at": None, "processing_started_at": None},
        {"ingest_id": "2", "service_name": "srv-b", "status": "completed", "metrics": {"total_logs": 20, "error_count": 0, "warning_count": 0, "critical_count": 0}, "created_at": t0, "environment": "dev", "object_key": "k2", "top_error": None, "report": None, "error_reason": None, "processed_at": None, "processing_started_at": None},
    ]
    for r in records:
        fake_repo.insert_record(r)

    response = client_with_repo.get("/metrics/summary?service_name=srv-a")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["service_name"] == "srv-a"
    assert data[0]["total_logs"] == 10


def test_metrics_summary_date_range_filter(client_with_repo: TestClient, fake_repo: FakeIngestionRepository):
    """Verifies that ?from=... and ?to=... date range queries correctly bound the aggregation."""
    t1 = datetime(2026, 9, 28, 8, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 9, 28, 16, 0, 0, tzinfo=timezone.utc)

    records = [
        {"ingest_id": "1", "service_name": "srv", "status": "completed", "metrics": {"total_logs": 10, "error_count": 0, "warning_count": 0, "critical_count": 0}, "created_at": t1, "environment": "dev", "object_key": "k1", "top_error": None, "report": None, "error_reason": None, "processed_at": None, "processing_started_at": None},
        {"ingest_id": "2", "service_name": "srv", "status": "completed", "metrics": {"total_logs": 20, "error_count": 0, "warning_count": 0, "critical_count": 0}, "created_at": t2, "environment": "dev", "object_key": "k2", "top_error": None, "report": None, "error_reason": None, "processed_at": None, "processing_started_at": None},
        {"ingest_id": "3", "service_name": "srv", "status": "completed", "metrics": {"total_logs": 30, "error_count": 0, "warning_count": 0, "critical_count": 0}, "created_at": t3, "environment": "dev", "object_key": "k3", "top_error": None, "report": None, "error_reason": None, "processed_at": None, "processing_started_at": None},
    ]
    for r in records:
        fake_repo.insert_record(r)

    # Filter from 10:00 to 14:00 (should only capture job 2 with 20 logs)
    from_str = "2026-09-28T10:00:00Z"
    to_str = "2026-09-28T14:00:00Z"
    response = client_with_repo.get(f"/metrics/summary?from={from_str}&to={to_str}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["total_logs"] == 20


def test_metrics_summary_db_error(client_with_repo: TestClient, fake_repo: FakeIngestionRepository):
    """Verifies that an underlying database aggregation failure returns HTTP 503."""
    fake_repo.should_fail_aggregate = True
    response = client_with_repo.get("/metrics/summary")
    assert response.status_code == 503
    assert "database service unavailable" in response.json()["detail"].lower()
