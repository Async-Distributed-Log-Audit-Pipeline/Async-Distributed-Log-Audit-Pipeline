"""
Configuration for the Log Ingestion API (AWS version).

In AWS Lambda all values come from environment variables set by template.yaml.
Credentials are NOT configured here: Lambda supplies temporary credentials from
its IAM execution role, so no access keys ever appear in code or environment.
For local development, `aws configure` credentials (or a .env file) are used.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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


@lru_cache()
def get_settings() -> Settings:
    return Settings()
