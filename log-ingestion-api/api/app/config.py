"""
Configuration management for the Log Ingestion API service.
Loads settings from environment variables and/or local .env file using pydantic-settings.
"""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration settings.
    All field names strictly match repository environment variable conventions.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server Configuration
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: str = "*"
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB size limit default

    # Messaging Queue Configuration (Supports "rabbitmq" or "sqs")
    QUEUE_TYPE: str = "rabbitmq"
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_QUEUE_NAME: str = "log-ingestion-queue"
    SQS_QUEUE_URL: str | None = None

    # Database Configuration (Supports "mongodb" or "dynamodb")
    DB_TYPE: str = "mongodb"
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "log_analytics"
    MONGO_COLLECTION: str = "ingestions"
    DYNAMODB_TABLE_NAME: str = "ingestions"

    # S3 / MinIO Object Storage Configuration
    # When deployed to AWS, leave S3_ENDPOINT_URL empty or None to use native AWS S3.
    S3_ENDPOINT_URL: str | None = "http://localhost:9000"
    S3_ACCESS_KEY: str | None = "minioadmin"
    S3_SECRET_KEY: str | None = "minioadmin"
    S3_BUCKET_NAME: str = "raw-logs"
    S3_REGION: str = "us-east-1"

    @property
    def cors_origins_list(self) -> List[str]:
        """
        Parses comma-separated CORS_ORIGINS string into a list of origin strings.
        If wildcard '*' is specified, returns ['*'].
        """
        if not self.CORS_ORIGINS or self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings factory function for FastAPI dependency injection.
    Allows settings to be overridden during testing via dependency_overrides.
    """
    return Settings()
