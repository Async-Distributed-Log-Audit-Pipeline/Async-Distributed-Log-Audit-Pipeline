"""Fakes package for unit and integration testing without external services."""
from tests.fakes.fake_repository import FakeIngestionRepository
from tests.fakes.fake_storage import FakeStorageClient
from tests.fakes.fake_queue import FakeQueueClient

__all__ = [
    "FakeIngestionRepository",
    "FakeStorageClient",
    "FakeQueueClient",
]
