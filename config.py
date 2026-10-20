"""
<<<<<<< HEAD
Configuration management for the Log Ingestion API service.
Loads settings from environment variables and/or local .env file using pydantic-settings.
"""

from functools import lru_cache
from typing import List
=======
Configuration for the Log Ingestion API (AWS version).

In AWS Lambda all values come from environment variables set by template.yaml.
Credentials are NOT configured here: Lambda supplies temporary credentials from
its IAM execution role, so no access keys ever appear in code or environment.
For local development, `aws configure` credentials (or a .env file) are used.
"""

from functools import lru_cache
from typing import List, Optional
>>>>>>> aws-cloud
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
<<<<<<< HEAD
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

    # RabbitMQ Configuration
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_QUEUE_NAME: str = "log-ingestion-queue"

    # MongoDB Configuration
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "log_analytics"
    MONGO_COLLECTION: str = "ingestions"

    # S3 / MinIO Object Storage Configuration
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
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
=======
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API behaviour
    CORS_ORIGINS: str = "*"
    # API Gateway (HTTP API) + Lambda cap a synchronous request payload at ~6 MB (base64 inflates uploads by ~33%).
    MAX_UPLOAD_BYTES: int = 4 * 1024 * 1024

    # Amazon SQS (replaces RabbitMQ)
    SQS_QUEUE_URL: str = ""

    # Amazon DynamoDB (replaces MongoDB)
    DDB_TABLE_NAME: str = "log-ingestions"

    # Amazon S3 (replaces MinIO)
    S3_BUCKET_NAME: str = "async-log-audit-bucket-nikeshala"
    AWS_REGION: str = "us-east-1"
    # Optional overrides, only for local emulators (LocalStack/MinIO). Leave unset on AWS.
    S3_ENDPOINT_URL: Optional[str] = None

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.CORS_ORIGINS or self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
>>>>>>> aws-cloud


@lru_cache()
def get_settings() -> Settings:
<<<<<<< HEAD
    """
    Cached settings factory function for FastAPI dependency injection.
    Allows settings to be overridden during testing via dependency_overrides.
    """
=======
>>>>>>> aws-cloud
    return Settings()
