"""
In-memory fake implementation of StorageClient for testing.
"""

from typing import BinaryIO, Dict, List
from app.clients.storage_client import StorageUnavailableError


class FakeStorageClient:
    """
    Fake storage client that records uploads and deletions in memory.
    Supports simulated failures for rollback verification.
    """

    def __init__(self):
        self.objects: Dict[str, bytes] = {}
        self.deleted_keys: List[str] = []
        self.calls: List[str] = []
        self.should_fail_upload = False

    def ensure_bucket_exists(self) -> None:
        self.calls.append("ensure_bucket_exists")

    def upload_fileobj(self, fileobj: BinaryIO, object_key: str) -> None:
        self.calls.append("upload_fileobj")
        if self.should_fail_upload:
            raise StorageUnavailableError("Simulated storage upload failure")
        data = fileobj.read()
        self.objects[object_key] = data

    def delete_file(self, object_key: str) -> None:
        self.calls.append("delete_file")
        self.deleted_keys.append(object_key)
        self.objects.pop(object_key, None)
