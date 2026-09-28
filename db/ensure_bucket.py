"""
Standalone script to ensure the S3 / MinIO raw-logs bucket exists.
Idempotent and safe to run on startup.
"""
import os
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

load_dotenv()

S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "raw-logs")
S3_REGION = os.getenv("S3_REGION", "us-east-1")


def ensure_bucket_exists():
    print(f"[*] Checking MinIO/S3 bucket '{S3_BUCKET_NAME}' at '{S3_ENDPOINT_URL}'...")
    s3_config = Config(s3={"addressing_style": "path"})
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name=S3_REGION,
            config=s3_config,
        )

        try:
            s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
            print(f"    [OK] Bucket '{S3_BUCKET_NAME}' already exists.")
        except ClientError as e:
            error_code = str(e.response.get("Error", {}).get("Code", ""))
            if error_code in ("404", "NoSuchBucket", "NotFound"):
                print(f"    [*] Bucket '{S3_BUCKET_NAME}' not found. Creating...")
                try:
                    if S3_REGION == "us-east-1":
                        s3_client.create_bucket(Bucket=S3_BUCKET_NAME)
                    else:
                        s3_client.create_bucket(
                            Bucket=S3_BUCKET_NAME,
                            CreateBucketConfiguration={"LocationConstraint": S3_REGION},
                        )
                    print(f"    [OK] Bucket '{S3_BUCKET_NAME}' created successfully.")
                except ClientError as create_err:
                    create_code = str(create_err.response.get("Error", {}).get("Code", ""))
                    if create_code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                        print(f"    [OK] Bucket '{S3_BUCKET_NAME}' already exists.")
                    else:
                        raise create_err
            elif error_code in ("403", "BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                print(f"    [OK] Bucket '{S3_BUCKET_NAME}' already exists.")
            else:
                raise e
    except (BotoCoreError, Exception) as e:
        print(f"    [ERROR] Failed to ensure bucket '{S3_BUCKET_NAME}': {e}")
        raise e


if __name__ == "__main__":
    ensure_bucket_exists()
