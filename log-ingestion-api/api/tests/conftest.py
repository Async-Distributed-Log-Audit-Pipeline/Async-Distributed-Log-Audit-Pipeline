"""
Pytest configuration and shared test fixtures for the Log Ingestion API.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure the 'api' directory is on the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.config import Settings, get_settings


@pytest.fixture
def test_settings() -> Settings:
    """Provides a controlled settings instance for testing."""
    return Settings(
        PORT=8000,
        HOST="0.0.0.0",
        CORS_ORIGINS="http://localhost:3000,http://example.com",
        MAX_UPLOAD_BYTES=10 * 1024 * 1024,
        SQS_QUEUE_URL="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
        DDB_TABLE_NAME="test-table",
        S3_BUCKET_NAME="test-bucket",
        AWS_REGION="us-east-1",
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    """FastAPI TestClient fixture configured with test settings override."""
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
