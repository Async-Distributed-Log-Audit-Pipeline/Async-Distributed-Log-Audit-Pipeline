import json
import os
import pytest

from errors import (
    DatabaseUnavailableError,
    InvalidLogFileError,
    ObjectNotFoundError,
    StorageUnavailableError,
)
from processor import Outcome, ProcessResult, process_message


class FakeRepo:
    def __init__(self, record=None):
        self.record = record
        self.marked_processing = False
        self.saved_results = None
        self.failed_reason = None
        self.mark_failed_should_raise_db_err = False
        self.mark_processing_return_val = True
        self.save_results_return_val = True
        self.find_by_id_should_raise_transient = False
        self.mark_processing_should_raise_transient = False

    def find_by_id(self, ingest_id):
        if self.find_by_id_should_raise_transient:
            raise DatabaseUnavailableError("DB connection timeout in find_by_id")
        return self.record

    def mark_processing(self, ingest_id):
        if self.mark_processing_should_raise_transient:
            raise DatabaseUnavailableError("DB connection timeout in mark_processing")
        self.marked_processing = True
        return self.mark_processing_return_val

    def save_results(self, ingest_id, metrics, report, top_error):
        self.saved_results = (metrics, report, top_error)
        return self.save_results_return_val

    def mark_failed(self, ingest_id, reason):
        if self.mark_failed_should_raise_db_err:
            raise DatabaseUnavailableError("DB error during mark_failed")
        self.failed_reason = reason
        return True


class FakeStorage:
    def __init__(self, content=None, raise_exc=None):
        self.content = content or json.dumps({"level": "INFO", "message": "Test log message"}).encode("utf-8")
        self.raise_exc = raise_exc
        self.downloaded_key = None

    def download_file(self, object_key, dest_path):
        if self.raise_exc:
            raise self.raise_exc
        self.downloaded_key = object_key
        with open(dest_path, "wb") as f:
            f.write(self.content)


def make_body(ingest_id="test-123", service_name="api-gateway", object_key="raw-logs/test-123.jsonl"):
    return json.dumps({
        "ingest_id": ingest_id,
        "service_name": service_name,
        "object_key": object_key,
    }).encode("utf-8")


def test_happy_path():
    record = {"ingest_id": "test-123", "status": "pending"}
    repo = FakeRepo(record)
    storage = FakeStorage()

    res = process_message(make_body(), repo, storage)

    assert isinstance(res, ProcessResult)
    assert res.outcome == Outcome.COMPLETED
    assert res.ingest_id == "test-123"
    assert repo.marked_processing is True
    assert repo.saved_results is not None
    assert storage.downloaded_key == "raw-logs/test-123.jsonl"


def test_duplicate_delivery_completed():
    record = {"ingest_id": "test-123", "status": "completed"}
    repo = FakeRepo(record)
    storage = FakeStorage()

    res = process_message(make_body(), repo, storage)

    assert res.outcome == Outcome.SKIPPED_DUPLICATE
    assert res.ingest_id == "test-123"
    assert repo.marked_processing is False


def test_already_failed_record():
    record = {"ingest_id": "test-123", "status": "failed"}
    repo = FakeRepo(record)
    storage = FakeStorage()

    res = process_message(make_body(), repo, storage)

    assert res.outcome == Outcome.SKIPPED_DUPLICATE
    assert res.ingest_id == "test-123"
    assert repo.marked_processing is False


def test_missing_record():
    repo = FakeRepo(record=None)
    storage = FakeStorage()

    res = process_message(make_body(), repo, storage)

    assert res.outcome == Outcome.INVALID_MESSAGE
    assert res.ingest_id == "test-123"
    assert repo.marked_processing is False


def test_invalid_malformed_message_body():
    repo = FakeRepo()
    storage = FakeStorage()

    # Case 1: Bad JSON syntax
    res_bad_json = process_message(b"NOT_VALID_JSON", repo, storage)
    assert res_bad_json.outcome == Outcome.INVALID_MESSAGE

    # Case 2: Missing required string field (object_key missing)
    bad_payload = json.dumps({"ingest_id": "test-123", "service_name": "api"}).encode("utf-8")
    res_missing_field = process_message(bad_payload, repo, storage)
    assert res_missing_field.outcome == Outcome.INVALID_MESSAGE


def test_permanent_error_marks_failed():
    record = {"ingest_id": "test-123", "status": "pending"}
    repo = FakeRepo(record)
    storage = FakeStorage(raise_exc=ObjectNotFoundError("Object key not found in S3"))

    res = process_message(make_body(), repo, storage)

    assert res.outcome == Outcome.FAILED_PERMANENT
    assert res.ingest_id == "test-123"
    assert repo.failed_reason is not None
    assert "Object key not found in S3" in repo.failed_reason


def test_transient_error_returns_retry_later():
    record = {"ingest_id": "test-123", "status": "pending"}
    repo = FakeRepo(record)
    storage = FakeStorage(raise_exc=StorageUnavailableError("S3 Connection timeout"))

    res = process_message(make_body(), repo, storage)

    assert res.outcome == Outcome.RETRY_LATER
    assert res.ingest_id == "test-123"
    assert repo.failed_reason is None  # Should NOT mark failed


def test_transient_error_in_find_by_id():
    repo = FakeRepo()
    repo.find_by_id_should_raise_transient = True
    storage = FakeStorage()

    res = process_message(make_body(), repo, storage)

    assert res.outcome == Outcome.RETRY_LATER
    assert res.ingest_id == "test-123"
    assert repo.marked_processing is False


def test_transient_error_in_mark_processing():
    record = {"ingest_id": "test-123", "status": "pending"}
    repo = FakeRepo(record)
    repo.mark_processing_should_raise_transient = True
    storage = FakeStorage()

    res = process_message(make_body(), repo, storage)

    assert res.outcome == Outcome.RETRY_LATER
    assert res.ingest_id == "test-123"


def test_unexpected_exception_marks_failed():
    record = {"ingest_id": "test-123", "status": "pending"}
    repo = FakeRepo(record)
    storage = FakeStorage(raise_exc=RuntimeError("Unexpected memory crash"))

    res = process_message(make_body(), repo, storage)

    assert res.outcome == Outcome.FAILED_PERMANENT
    assert res.ingest_id == "test-123"
    assert repo.failed_reason is not None
    assert "unexpected error: RuntimeError" in repo.failed_reason


def test_processing_leftover_completed():
    record = {"ingest_id": "test-123", "status": "processing"}
    repo = FakeRepo(record)
    storage = FakeStorage()

    res = process_message(make_body(), repo, storage)

    assert res.outcome == Outcome.COMPLETED
    assert res.ingest_id == "test-123"
    assert repo.saved_results is not None


def test_save_results_returns_false():
    record = {"ingest_id": "test-123", "status": "pending"}
    repo = FakeRepo(record)
    repo.save_results_return_val = False
    storage = FakeStorage()

    res = process_message(make_body(), repo, storage)

    assert res.outcome == Outcome.SKIPPED_DUPLICATE
    assert res.ingest_id == "test-123"


def test_mark_failed_raises_transient_error():
    record = {"ingest_id": "test-123", "status": "pending"}
    repo = FakeRepo(record)
    repo.mark_failed_should_raise_db_err = True
    storage = FakeStorage(raise_exc=ObjectNotFoundError("Object not found"))

    res = process_message(make_body(), repo, storage)

    assert res.outcome == Outcome.RETRY_LATER
    assert res.ingest_id == "test-123"
