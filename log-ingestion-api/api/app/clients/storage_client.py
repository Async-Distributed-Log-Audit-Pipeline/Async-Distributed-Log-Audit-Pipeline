"""
S3 / MinIO Object Storage Client.
Handles file uploads, rollbacks, and automatic bucket verification using boto3.
"""

import logging
from typing import BinaryIO, Optional
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class StorageUnavailableError(Exception):
    """Raised when S3 / MinIO storage operations fail due to infrastructure/connection issues."""
    pass


class StorageClient:
    """
    Client for interacting with S3-compatible object storage (MinIO).
    Uses path-style addressing and ensures target bucket availability.
    """

    def __init__(
        self,
        endpoint_url: str = "http://localhost:9000",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        bucket_name: str = "raw-logs",
        region: str = "us-east-1",
    ):
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.region = region

        s3_config = Config(s3={"addressing_style": "path"})
        try:
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
                config=s3_config,
            )
        except Exception as e:
            logger.error("Failed to initialize S3 client: %s", e)
            raise StorageUnavailableError(f"Storage client initialization error: {e}") from e

    def ensure_bucket_exists(self) -> None:
        """
        Verifies that the target bucket exists, creating it if absent.
        Matches log-worker dev setup behavior.
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchBucket", "NotFound"):
                logger.info("Bucket '%s' does not exist. Creating...", self.bucket_name)
                try:
                    if self.region == "us-east-1":
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={"LocationConstraint": self.region},
                        )
                    logger.info("Bucket '%s' created successfully.", self.bucket_name)
                except Exception as create_err:
                    logger.error("Failed to create bucket '%s': %s", self.bucket_name, create_err)
                    raise StorageUnavailableError(f"Failed to create bucket: {create_err}") from create_err
            else:
                logger.error("Error inspecting bucket '%s': %s", self.bucket_name, e)
                raise StorageUnavailableError(f"Error accessing bucket: {e}") from e
        except (BotoCoreError, Exception) as e:
            logger.error("S3 connection error checking bucket: %s", e)
            raise StorageUnavailableError(f"Storage service unavailable: {e}") from e

    def upload_fileobj(self, fileobj: BinaryIO, object_key: str) -> None:
        """
        Uploads a stream/file-like object to object storage.
        """
        try:
            self.s3_client.upload_fileobj(fileobj, self.bucket_name, object_key)
        except ClientError as e:
            logger.error("S3 client error uploading '%s': %s", object_key, e)
            raise StorageUnavailableError(f"S3 upload error: {e}") from e
        except (BotoCoreError, Exception) as e:
            logger.error("Storage service error uploading '%s': %s", object_key, e)
            raise StorageUnavailableError(f"Storage service unavailable: {e}") from e

    def delete_file(self, object_key: str) -> None:
        """
        Deletes an object from storage. Used for best-effort rollback during upload failures.
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)
            logger.info("Cleaned up orphaned object '%s' from bucket '%s'.", object_key, self.bucket_name)
        except Exception as e:
            logger.warning("Failed to delete object '%s' during rollback: %s", object_key, e)


def get_storage_client(
    settings: Settings = Depends(get_settings),
) -> StorageClient:
    """FastAPI dependency provider for StorageClient."""
    return StorageClient(
        endpoint_url=settings.S3_ENDPOINT_URL,
        access_key=settings.S3_ACCESS_KEY,
        secret_key=settings.S3_SECRET_KEY,
        bucket_name=settings.S3_BUCKET_NAME,
        region=settings.S3_REGION,
    )
