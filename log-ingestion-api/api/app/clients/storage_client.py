"""
Amazon S3 storage client: stores the raw uploaded log files.
The bucket is created by infrastructure (see README / template.yaml), not by application code.
"""

import logging
from functools import lru_cache
from typing import BinaryIO, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class StorageUnavailableError(Exception):
    """Raised when S3 operations fail."""


class StorageClient:
    def __init__(self, bucket_name: str, region: str = "us-east-1", endpoint_url: Optional[str] = None):
        self.bucket_name = bucket_name
        self.region = region
        try:
            self.s3_client = boto3.client("s3", region_name=region, endpoint_url=endpoint_url)
        except Exception as e:
            raise StorageUnavailableError(f"Storage client initialization error: {e}") from e

    def ensure_bucket_exists(self) -> None:
        """Kept for interface compatibility; the bucket is provisioned outside the app."""
        return None

    def upload_fileobj(self, fileobj: BinaryIO, object_key: str) -> None:
        try:
            self.s3_client.upload_fileobj(
                fileobj,
                self.bucket_name,
                object_key,
                ExtraArgs={"ServerSideEncryption": "AES256"},
            )
        except (ClientError, BotoCoreError, Exception) as e:
            logger.error("S3 error uploading '%s': %s", object_key, e)
            raise StorageUnavailableError(f"S3 upload error: {e}") from e

    def delete_file(self, object_key: str) -> None:
        """Best-effort rollback when a later step (DB/queue) fails."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)
            logger.info("Cleaned up orphaned object '%s'.", object_key)
        except Exception as e:
            logger.warning("Failed to delete object '%s' during rollback: %s", object_key, e)


@lru_cache(maxsize=4)
def _build_storage_client(bucket: str, region: str, endpoint_url: Optional[str]) -> StorageClient:
    return StorageClient(bucket_name=bucket, region=region, endpoint_url=endpoint_url)


def get_storage_client(settings: Settings = Depends(get_settings)) -> StorageClient:
    return _build_storage_client(settings.S3_BUCKET_NAME, settings.AWS_REGION, settings.S3_ENDPOINT_URL)
