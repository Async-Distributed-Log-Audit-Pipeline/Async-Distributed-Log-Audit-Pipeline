import os
import boto3
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    EndpointConnectionError,
    ConnectTimeoutError,
    ReadTimeoutError,
)
from errors import ObjectNotFoundError, StorageUnavailableError


class ObjectStorageClient:
    """
    Amazon S3 client used by the worker to download raw log files.
    Credentials come from the Lambda execution role (no access keys in code).
    """

    def __init__(self, bucket_name: str | None = None, region: str | None = None, endpoint_url: str | None = None):
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME", "async-log-audit-bucket-nikeshala")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.endpoint_url = endpoint_url or os.getenv("S3_ENDPOINT_URL") or None
        try:
            self.s3_client = boto3.client("s3", region_name=self.region, endpoint_url=self.endpoint_url)
        except Exception as e:
            raise StorageUnavailableError(f"Failed to initialize S3 client: {e}") from e

    def ensure_bucket_exists(self) -> None:
        """
        Verifies that the target bucket exists, creating it if absent.
        Idempotent and handles existing buckets silently.
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = str(e.response.get("Error", {}).get("Code", ""))
            if error_code in ("404", "NoSuchBucket", "NotFound"):
                try:
                    if self.region == "us-east-1":
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={"LocationConstraint": self.region},
                        )
                except ClientError as create_err:
                    create_code = str(create_err.response.get("Error", {}).get("Code", ""))
                    if create_code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                        raise StorageUnavailableError(f"Failed to create bucket: {create_err}") from create_err
            elif error_code not in ("403", "BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                raise StorageUnavailableError(f"Error accessing bucket: {e}") from e
        except (BotoCoreError, Exception) as e:
            raise StorageUnavailableError(f"Storage service unavailable: {e}") from e

    def download_file(self, object_key: str, dest_path: str) -> None:
        """
        Downloads a file from object storage directly to disk without loading it into memory.
        """
        try:
            dest_dir = os.path.dirname(dest_path)
            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)

            self.s3_client.download_file(self.bucket_name, object_key, dest_path)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchKey", "NotFound"):
                raise ObjectNotFoundError(
                    f"Object '{object_key}' not found in bucket '{self.bucket_name}'."
                ) from e
            elif error_code and str(error_code).startswith("5"):
                raise StorageUnavailableError(
                    f"Storage server error ({error_code}) while downloading '{object_key}': {e}"
                ) from e
            else:
                raise StorageUnavailableError(
                    f"S3 client error downloading '{object_key}': {e}"
                ) from e
        except (BotoCoreError, EndpointConnectionError, ConnectTimeoutError, ReadTimeoutError) as e:
            raise StorageUnavailableError(
                f"Storage service unavailable while downloading '{object_key}': {e}"
            ) from e
        except Exception as e:
            raise StorageUnavailableError(
                f"Unexpected error downloading '{object_key}': {e}"
            ) from e

    def upload_file(self, file_path: str, object_key: str) -> None:
        """
        Uploads a local file to object storage. Ensures bucket exists first.
        """
        self.ensure_bucket_exists()
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, object_key)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code and str(error_code).startswith("5"):
                raise StorageUnavailableError(
                    f"Storage server error ({error_code}) while uploading '{object_key}': {e}"
                ) from e
            raise StorageUnavailableError(f"S3 client error uploading '{object_key}': {e}") from e
        except (BotoCoreError, EndpointConnectionError, ConnectTimeoutError, ReadTimeoutError) as e:
            raise StorageUnavailableError(
                f"Storage service unavailable while uploading '{object_key}': {e}"
            ) from e
        except Exception as e:
            raise StorageUnavailableError(f"Unexpected error uploading '{object_key}': {e}") from e
