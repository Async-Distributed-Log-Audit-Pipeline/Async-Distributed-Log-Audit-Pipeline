"""
Unit and integration tests for log endpoints:
- Ingestion upload (valid jsonl, valid jsonl.gz, validation failures)
- Error handling and transaction rollbacks (storage failure, db failure, queue failure)
- Order of execution verification (Storage -> DB -> Queue)
- Status lookup and log listing
"""

from datetime import datetime, timezone, timedelta
import gzip
import io
import json
import pytest
from fastapi.testclient import TestClient

from app.clients.queue_client import get_queue_client
from app.clients.storage_client import get_storage_client
from app.config import Settings, get_settings
from app.main import app
from app.repositories.ingestion_repository import get_ingestion_repository
from tests.fakes.fake_queue import FakeQueueClient
from tests.fakes.fake_repository import FakeIngestionRepository
from tests.fakes.fake_storage import FakeStorageClient


@pytest.fixture
def fake_repo():
    return FakeIngestionRepository()


@pytest.fixture
def fake_storage():
    return FakeStorageClient()


@pytest.fixture
def fake_queue():
    return FakeQueueClient()


@pytest.fixture
def tracker():
    """Tracks sequence of operations across services to verify call order."""
    return []


@pytest.fixture
def client_with_fakes(
    client: TestClient,
    fake_repo: FakeIngestionRepository,
    fake_storage: FakeStorageClient,
    fake_queue: FakeQueueClient,
    tracker: list,
):
    # Intercept calls to record the execution timeline
    orig_upload = fake_storage.upload_fileobj
    orig_insert = fake_repo.insert_record
    orig_publish = fake_queue.publish_job

    def tracked_upload(fileobj, object_key):
        tracker.append("storage_upload")
        return orig_upload(fileobj, object_key)

    def tracked_insert(record):
        tracker.append("db_insert")
        return orig_insert(record)

    def tracked_publish(payload):
        tracker.append("queue_publish")
        return orig_publish(payload)

    fake_storage.upload_fileobj = tracked_upload
    fake_repo.insert_record = tracked_insert
    fake_queue.publish_job = tracked_publish

    app.dependency_overrides[get_storage_client] = lambda: fake_storage
    app.dependency_overrides[get_ingestion_repository] = lambda: fake_repo
    app.dependency_overrides[get_queue_client] = lambda: fake_queue

    yield client

    app.dependency_overrides.pop(get_storage_client, None)
    app.dependency_overrides.pop(get_ingestion_repository, None)
    app.dependency_overrides.pop(get_queue_client, None)


# ==========================================
# 1. Upload Success Tests & Flow Order
# ==========================================

def test_upload_valid_jsonl(
    client_with_fakes: TestClient,
    fake_repo: FakeIngestionRepository,
    fake_storage: FakeStorageClient,
    fake_queue: FakeQueueClient,
    tracker: list,
):
    """
    Verifies valid .jsonl upload:
    - Returns 201 with ingest_id and pending status
    - Executes strictly in order: Storage -> DB -> Queue
    - Object is stored in S3/MinIO
    - DB record created with correct fields
    - Queue message dispatched with correct payload
    """
    valid_content = b'{"timestamp":"2026-09-28T12:00:00Z","level":"INFO","message":"User login success"}\n'
    files = {"file": ("api_logs.jsonl", io.BytesIO(valid_content), "application/json")}
    data = {"service_name": "auth-service", "environment": "dev"}

    response = client_with_fakes.post("/logs/upload", files=files, data=data)
    assert response.status_code == 201
    resp_data = response.json()
    assert "ingest_id" in resp_data
    assert resp_data["status"] == "pending"

    ingest_id = resp_data["ingest_id"]
    expected_object_key = f"raw-logs/auth-service-{ingest_id}.jsonl"

    # Verify call order: Storage -> DB -> Queue
    assert tracker == ["storage_upload", "db_insert", "queue_publish"]

    # Verify Storage
    assert expected_object_key in fake_storage.objects
    assert fake_storage.objects[expected_object_key] == valid_content

    # Verify DB
    record = fake_repo.find_by_id(ingest_id)
    assert record is not None
    assert record["service_name"] == "auth-service"
    assert record["environment"] == "dev"
    assert record["object_key"] == expected_object_key
    assert record["status"] == "pending"
    assert record["metrics"] is None
    assert record["top_error"] is None
    assert record["report"] is None
    assert record["error_reason"] is None
    assert record["created_at"] is not None

    # Verify Queue
    assert len(fake_queue.messages) == 1
    msg = fake_queue.messages[0]
    assert msg["ingest_id"] == ingest_id
    assert msg["service_name"] == "auth-service"
    assert msg["object_key"] == expected_object_key


def test_upload_valid_jsonl_gz(
    client_with_fakes: TestClient,
    fake_repo: FakeIngestionRepository,
    fake_storage: FakeStorageClient,
    fake_queue: FakeQueueClient,
):
    """Verifies that compressed .jsonl.gz logs are accepted and decompressed streaming for sanity checks."""
    raw_lines = b'{"timestamp":"2026-09-28T12:00:00Z","level":"WARN","message":"Memory usage high"}\n'
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(raw_lines)
    gz_bytes = buf.getvalue()

    files = {"file": ("app.jsonl.gz", io.BytesIO(gz_bytes), "application/gzip")}
    data = {"service_name": "payment-service", "environment": "production"}

    response = client_with_fakes.post("/logs/upload", files=files, data=data)
    assert response.status_code == 201
    resp_data = response.json()
    ingest_id = resp_data["ingest_id"]

    expected_key = f"raw-logs/payment-service-{ingest_id}.jsonl.gz"
    assert expected_key in fake_storage.objects
    assert fake_storage.objects[expected_key] == gz_bytes


# ==========================================
# 2. Input Validation Tests
# ==========================================

def test_upload_oversize_file(client_with_fakes: TestClient):
    """Verifies that files exceeding MAX_UPLOAD_BYTES are rejected with HTTP 413 while streaming."""
    # Temporarily set max upload to 50 bytes
    custom_settings = Settings(MAX_UPLOAD_BYTES=50)
    app.dependency_overrides[get_settings] = lambda: custom_settings

    large_content = b'{"level":"INFO","message":"' + b"A" * 100 + b'"}\n'
    files = {"file": ("big.jsonl", io.BytesIO(large_content), "application/json")}
    data = {"service_name": "gateway"}

    try:
        response = client_with_fakes.post("/logs/upload", files=files, data=data)
        assert response.status_code == 413
        assert "exceeds maximum allowed size" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_upload_empty_file(client_with_fakes: TestClient):
    """Verifies that uploading an empty (0-byte) file returns HTTP 400."""
    files = {"file": ("empty.jsonl", io.BytesIO(b""), "application/json")}
    data = {"service_name": "gateway"}

    response = client_with_fakes.post("/logs/upload", files=files, data=data)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_bad_content_invalid_json(client_with_fakes: TestClient):
    """Verifies that non-JSON content is rejected with HTTP 400."""
    files = {"file": ("invalid.jsonl", io.BytesIO(b"NOT_A_VALID_JSON_OBJECT\n"), "application/json")}
    data = {"service_name": "gateway"}

    response = client_with_fakes.post("/logs/upload", files=files, data=data)
    assert response.status_code == 400
    assert "invalid log file content" in response.json()["detail"].lower()


def test_upload_bad_extension(client_with_fakes: TestClient):
    """Verifies that disallowed file extensions (.txt, .log, etc.) return HTTP 400."""
    files = {"file": ("logs.txt", io.BytesIO(b'{"level":"INFO"}\n'), "text/plain")}
    data = {"service_name": "gateway"}

    response = client_with_fakes.post("/logs/upload", files=files, data=data)
    assert response.status_code == 400
    assert "invalid file extension" in response.json()["detail"].lower()


def test_upload_missing_service_name(client_with_fakes: TestClient):
    """Verifies that omitting the required service_name field returns HTTP 422."""
    files = {"file": ("logs.jsonl", io.BytesIO(b'{"level":"INFO"}\n'), "application/json")}
    # data without service_name
    response = client_with_fakes.post("/logs/upload", files=files, data={})
    assert response.status_code == 422


@pytest.mark.parametrize(
    "bad_name",
    [
        "service/nested",
        "service\\nested",
        "../traversal",
        "service name with spaces",
        "service@bad!",
    ],
)
def test_upload_unsafe_service_name(client_with_fakes: TestClient, bad_name: str):
    """Verifies that service_name with invalid/traversal characters is rejected with HTTP 400."""
    files = {"file": ("logs.jsonl", io.BytesIO(b'{"level":"INFO"}\n'), "application/json")}
    data = {"service_name": bad_name}

    response = client_with_fakes.post("/logs/upload", files=files, data=data)
    assert response.status_code == 400
    assert "invalid service_name" in response.json()["detail"].lower()


# ==========================================
# 3. Transactional Failure Path Tests
# ==========================================

def test_failure_path_storage_fails(
    client_with_fakes: TestClient,
    fake_storage: FakeStorageClient,
    fake_repo: FakeIngestionRepository,
    fake_queue: FakeQueueClient,
):
    """
    Step 3 fails:
    - Storage upload fails.
    - Returns 503.
    - Nothing is written to MongoDB or RabbitMQ.
    """
    fake_storage.should_fail_upload = True
    files = {"file": ("logs.jsonl", io.BytesIO(b'{"level":"INFO"}\n'), "application/json")}
    data = {"service_name": "gateway"}

    response = client_with_fakes.post("/logs/upload", files=files, data=data)
    assert response.status_code == 503
    assert "storage service unavailable" in response.json()["detail"].lower()

    # Nothing created
    assert len(fake_repo.records) == 0
    assert len(fake_queue.messages) == 0


def test_failure_path_db_fails_and_storage_cleaned_up(
    client_with_fakes: TestClient,
    fake_storage: FakeStorageClient,
    fake_repo: FakeIngestionRepository,
    fake_queue: FakeQueueClient,
):
    """
    Step 4 fails:
    - Database insert fails.
    - Returns 503.
    - The object uploaded in Step 3 is deleted from storage (best-effort rollback).
    - No message is sent to RabbitMQ.
    """
    fake_repo.should_fail_insert = True
    files = {"file": ("logs.jsonl", io.BytesIO(b'{"level":"INFO"}\n'), "application/json")}
    data = {"service_name": "gateway"}

    response = client_with_fakes.post("/logs/upload", files=files, data=data)
    assert response.status_code == 503
    assert "database service unavailable" in response.json()["detail"].lower()

    # Storage object was cleaned up
    assert len(fake_storage.deleted_keys) == 1
    assert len(fake_storage.objects) == 0

    # No message sent to queue
    assert len(fake_queue.messages) == 0


def test_failure_path_queue_fails_and_record_marked_failed(
    client_with_fakes: TestClient,
    fake_repo: FakeIngestionRepository,
    fake_queue: FakeQueueClient,
):
    """
    Step 5 fails:
    - RabbitMQ publish fails.
    - Returns 503.
    - Record in MongoDB is transitioned to status='failed' with error_reason.
    - Nothing stays in 'pending' state.
    """
    fake_queue.should_fail_publish = True
    files = {"file": ("logs.jsonl", io.BytesIO(b'{"level":"INFO"}\n'), "application/json")}
    data = {"service_name": "gateway"}

    response = client_with_fakes.post("/logs/upload", files=files, data=data)
    assert response.status_code == 503
    assert "message queue service unavailable" in response.json()["detail"].lower()

    # Record in DB must be 'failed', not 'pending'
    assert len(fake_repo.records) == 1
    record = list(fake_repo.records.values())[0]
    assert record["status"] == "failed"
    assert record["error_reason"] is not None
    assert "Failed to publish" in record["error_reason"]


# ==========================================
# 4. Status and List Endpoint Tests
# ==========================================

def test_get_log_status_found(client_with_fakes: TestClient, fake_repo: FakeIngestionRepository):
    """Verifies that an existing ingestion record is returned without internal MongoDB _id."""
    ingest_id = "test-uuid-1234"
    record = {
        "ingest_id": ingest_id,
        "service_name": "auth-service",
        "environment": "staging",
        "object_key": f"raw-logs/auth-service-{ingest_id}.jsonl",
        "status": "completed",
        "metrics": {"total_logs": 100, "error_count": 2, "warning_count": 5, "critical_count": 0},
        "top_error": "Invalid token",
        "report": {"health": "degraded"},
        "error_reason": None,
        "created_at": datetime.now(timezone.utc),
        "processed_at": datetime.now(timezone.utc),
        "processing_started_at": datetime.now(timezone.utc),
    }
    fake_repo.insert_record(record)

    response = client_with_fakes.get(f"/logs/status?id={ingest_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["ingest_id"] == ingest_id
    assert data["service_name"] == "auth-service"
    assert data["status"] == "completed"
    assert data["metrics"]["total_logs"] == 100
    assert "_id" not in data


def test_get_log_status_not_found(client_with_fakes: TestClient):
    """Verifies that querying a non-existent ingest_id returns HTTP 404."""
    response = client_with_fakes.get("/logs/status?id=non-existent-uuid")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_log_status_db_error(client_with_fakes: TestClient, fake_repo: FakeIngestionRepository):
    """Verifies that a database connectivity error returns HTTP 503."""
    fake_repo.should_fail_find = True
    response = client_with_fakes.get("/logs/status?id=any-uuid")
    assert response.status_code == 503
    assert "database service unavailable" in response.json()["detail"].lower()


def test_list_logs_pagination_and_sorting(client_with_fakes: TestClient, fake_repo: FakeIngestionRepository):
    """Verifies that GET /logs returns records sorted newest first with pagination."""
    base_time = datetime(2026, 9, 28, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(5):
        record = {
            "ingest_id": f"uuid-{i}",
            "service_name": "api-gateway",
            "environment": "dev",
            "object_key": f"raw-logs/api-gateway-uuid-{i}.jsonl",
            "status": "pending",
            "metrics": None,
            "top_error": None,
            "report": None,
            "error_reason": None,
            "created_at": base_time + timedelta(minutes=i),
            "processed_at": None,
            "processing_started_at": None,
        }
        fake_repo.insert_record(record)

    # Test limit=2, skip=0 (newest: uuid-4, uuid-3)
    response = client_with_fakes.get("/logs?limit=2&skip=0")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert items[0]["ingest_id"] == "uuid-4"
    assert items[1]["ingest_id"] == "uuid-3"
    assert "_id" not in items[0]

    # Test skip=2 (uuid-2, uuid-1)
    response_skip = client_with_fakes.get("/logs?limit=2&skip=2")
    assert response_skip.status_code == 200
    items_skip = response_skip.json()
    assert len(items_skip) == 2
    assert items_skip[0]["ingest_id"] == "uuid-2"
    assert items_skip[1]["ingest_id"] == "uuid-1"


def test_list_logs_filters(client_with_fakes: TestClient, fake_repo: FakeIngestionRepository):
    """Verifies filtering by service_name, status, and environment."""
    t0 = datetime.now(timezone.utc)
    records = [
        {"ingest_id": "r1", "service_name": "srv-a", "environment": "dev", "status": "completed", "created_at": t0, "object_key": "k1", "metrics": None, "top_error": None, "report": None, "error_reason": None, "processed_at": None, "processing_started_at": None},
        {"ingest_id": "r2", "service_name": "srv-a", "environment": "prod", "status": "pending", "created_at": t0, "object_key": "k2", "metrics": None, "top_error": None, "report": None, "error_reason": None, "processed_at": None, "processing_started_at": None},
        {"ingest_id": "r3", "service_name": "srv-b", "environment": "dev", "status": "failed", "created_at": t0, "object_key": "k3", "metrics": None, "top_error": None, "report": None, "error_reason": None, "processed_at": None, "processing_started_at": None},
    ]
    for r in records:
        fake_repo.insert_record(r)

    # Filter service_name=srv-a
    res = client_with_fakes.get("/logs?service_name=srv-a")
    assert res.status_code == 200
    assert len(res.json()) == 2

    # Filter environment=prod
    res = client_with_fakes.get("/logs?environment=prod")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["ingest_id"] == "r2"

    # Filter status=failed
    res = client_with_fakes.get("/logs?status=failed")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["ingest_id"] == "r3"


def test_list_logs_db_error(client_with_fakes: TestClient, fake_repo: FakeIngestionRepository):
    """Verifies that a database connectivity error during listing returns HTTP 503."""
    fake_repo.should_fail_find = True
    response = client_with_fakes.get("/logs")
    assert response.status_code == 503
    assert "database service unavailable" in response.json()["detail"].lower()
