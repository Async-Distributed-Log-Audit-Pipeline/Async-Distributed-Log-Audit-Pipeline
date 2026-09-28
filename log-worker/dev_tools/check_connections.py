import os
import sys
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
import pymongo
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# MongoDB configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "log_analytics")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "ingestions")

# S3 configuration
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "raw-logs")
S3_REGION = os.getenv("S3_REGION", "us-east-1")


def check_mongodb() -> bool:
    print(f"[+] Checking MongoDB connection at '{MONGO_URI}'...")
    try:
        # Short timeout for dev connectivity check
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Ping administrative command to verify server availability
        res = client.admin.command('ping')
        print(f"    [OK] MongoDB connected successfully: {res}")
        return True
    except PyMongoError as e:
        print(f"    [ERROR] MongoDB connection failed: {e}", file=sys.stderr)
        return False


def check_s3() -> bool:
    print(f"[+] Checking S3 Object Storage (MinIO) at '{S3_ENDPOINT_URL}'...")
    try:
        # Use path-style addressing for S3 compatible endpoints (MinIO)
        s3_config = Config(s3={'addressing_style': 'path'})
        s3_client = boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name=S3_REGION,
            config=s3_config
        )

        # Check if bucket exists, create if missing
        try:
            s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
            print(f"    [OK] S3 Bucket '{S3_BUCKET_NAME}' already exists.")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code in ('404', 'NoSuchBucket', 'NotFound'):
                print(f"    [*] Bucket '{S3_BUCKET_NAME}' not found. Creating bucket...")
                if S3_REGION == 'us-east-1':
                    s3_client.create_bucket(Bucket=S3_BUCKET_NAME)
                else:
                    s3_client.create_bucket(
                        Bucket=S3_BUCKET_NAME,
                        CreateBucketConfiguration={'LocationConstraint': S3_REGION}
                    )
                print(f"    [OK] Bucket '{S3_BUCKET_NAME}' created successfully.")
            else:
                raise e

        # List buckets to confirm connectivity and permissions
        buckets_resp = s3_client.list_buckets()
        bucket_names = [b['Name'] for b in buckets_resp.get('Buckets', [])]
        print(f"    [OK] S3 connection successful. Existing buckets: {bucket_names}")
        return True
    except (BotoCoreError, ClientError, Exception) as e:
        print(f"    [ERROR] S3 connection/bucket setup failed: {e}", file=sys.stderr)
        return False


def main():
    print("=== Starting Dev Environment Connectivity Checks ===\n")
    mongo_ok = check_mongodb()
    print()
    s3_ok = check_s3()
    print()

    if mongo_ok and s3_ok:
        print("=== All connectivity checks PASSED ===")
        sys.exit(0)
    else:
        print("=== Connectivity checks FAILED ===", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
