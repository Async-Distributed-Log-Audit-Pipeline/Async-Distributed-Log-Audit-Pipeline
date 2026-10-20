"""
In-memory fake implementation of QueueClient for testing.
"""

from typing import Any, Dict, List
from app.clients.queue_client import QueueUnavailableError


class FakeQueueClient:
    """
    Fake RabbitMQ client that records published messages in memory.
    Supports simulated failures to test queue failure handling and rollback.
    """

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.calls: List[str] = []
        self.should_fail_publish = False

    def publish_job(self, payload: Dict[str, Any]) -> None:
        self.calls.append("publish_job")
        if self.should_fail_publish:
            raise QueueUnavailableError("Simulated RabbitMQ publishing failure")
        self.messages.append(payload)
