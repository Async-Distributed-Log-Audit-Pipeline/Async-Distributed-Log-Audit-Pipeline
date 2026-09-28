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
        RABBITMQ_HOST="localhost",
        RABBITMQ_PORT=5672,
        RABBITMQ_USER="guest",
        RABBITMQ_PASSWORD="guest",
        RABBITMQ_QUEUE_NAME="log-ingestion-queue",
        MONGO_URI="mongodb://localhost:27017",
        MONGO_DB_NAME="log_analytics",
        MONGO_COLLECTION="ingestions",
        S3_ENDPOINT_URL="http://localhost:9000",
        S3_ACCESS_KEY="minioadmin",
        S3_SECRET_KEY="minioadmin",
        S3_BUCKET_NAME="raw-logs",
        S3_REGION="us-east-1",
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    """FastAPI TestClient fixture configured with test settings override."""
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
